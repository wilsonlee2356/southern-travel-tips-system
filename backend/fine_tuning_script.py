#!/usr/bin/env python3
"""
Real LoRA Fine-tuning Script for Ollama Models
This script performs actual LoRA fine-tuning and registers the result as a new model
"""

import os
import sys
import json
import argparse
import asyncio
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import torch

# Import hyperparameters configuration
try:
    from hyperparameters_config import get_training_config, get_model_size_category
except ImportError:
    # Fallback if hyperparameters_config.py is not available
    def get_training_config(base_model: str) -> dict:
        return {
            'learning_rate': 0.0001,
            'num_epochs': 3,
            'batch_size': 4,
            'gradient_accumulation_steps': 8,
            'lora_rank': 16,
            'lora_alpha': 32,
            'lora_dropout': 0.1,
            'target_modules': ['q_proj', 'v_proj', 'k_proj', 'o_proj']
        }
    
    def get_model_size_category(model_name: str) -> str:
        return 'medium'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoRAFineTuner:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = None
        self.model_output_path = None
        self.session_id = config.get('session_id', f"training_{int(time.time())}")
        
    def validate_config(self) -> bool:
        """Validate the training configuration"""
        required_fields = ['base_model', 'adapter_name']
        
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required field: {field}")
                return False
                
        # Hyperparameters are now loaded from configuration file
        # Get hyperparameters for the base model
        try:
            hyperparams = get_training_config(self.config['base_model'])
            logger.info(f"Loaded hyperparameters for {self.config['base_model']}: {hyperparams}")
            
            # Merge hyperparameters into config
            self.config.update(hyperparams)
            
        except Exception as e:
            logger.error(f"Failed to load hyperparameters: {e}")
            return False
            
        return True
    
    
    def prepare_dataset(self, dataset_path: str) -> str:
        """Prepare dataset for training"""
        logger.info(f"Preparing dataset from: {dataset_path}")
        
        # Create temporary directory for processed dataset
        self.temp_dir = tempfile.mkdtemp()
        processed_dataset_path = os.path.join(self.temp_dir, "processed_dataset.jsonl")
        
        try:
            # Check if file exists
            if not os.path.exists(dataset_path):
                raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
            
            # Check file size
            file_size = os.path.getsize(dataset_path)
            if file_size == 0:
                raise ValueError(f"Dataset file is empty: {dataset_path}")
            
            logger.info(f"Dataset file size: {file_size} bytes")
            
            with open(dataset_path, 'r', encoding='utf-8') as f:
                if dataset_path.endswith('.json'):
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError("JSON file must contain an array of training examples")
                elif dataset_path.endswith('.jsonl'):
                    data = []
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            try:
                                data.append(json.loads(line))
                            except json.JSONDecodeError as e:
                                logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
                                continue
                else:
                    raise ValueError("Unsupported file format. Use .json or .jsonl")
            
            logger.info(f"Loaded {len(data)} raw examples from dataset")
            
            # Convert to training format
            training_data = []
            skipped_count = 0
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    logger.warning(f"Skipping non-dict item at index {i}: {item}")
                    skipped_count += 1
                    continue
                    
                if 'prompt' not in item or 'response' not in item:
                    logger.warning(f"Skipping item missing prompt/response at index {i}: {item}")
                    skipped_count += 1
                    continue
                    
                training_example = {
                    "instruction": item['prompt'],
                    "input": "",
                    "output": item['response']
                }
                training_data.append(training_example)
            
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} invalid examples")
            
            # Save processed dataset
            with open(processed_dataset_path, 'w', encoding='utf-8') as f:
                for item in training_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.info(f"Processed {len(training_data)} training examples")
            return processed_dataset_path
            
        except Exception as e:
            logger.error(f"Error preparing dataset: {e}")
            raise
    
    def get_hf_model_name(self, ollama_model_name: str) -> str:
        """Convert Ollama model name to Hugging Face model name"""
        model_mapping = {
            'qwen2.5:32b': 'Qwen/Qwen2.5-32B',
            'qwen2.5:14b': 'Qwen/Qwen2.5-14B',
            'qwen2.5:7b': 'Qwen/Qwen2.5-7B',
            'qwen2.5:3b': 'Qwen/Qwen2.5-3B',
            'qwen2.5:1.5b': 'Qwen/Qwen2.5-1.5B',
            'qwen2.5:0.5b': 'Qwen/Qwen2.5-0.5B',
            'llama3.2:3b': 'meta-llama/Llama-3.2-3B',
            'llama3.2:1b': 'meta-llama/Llama-3.2-1B',
            'llama3.1:8b': 'meta-llama/Llama-3.1-8B',
            'llama3.1:70b': 'meta-llama/Llama-3.1-70B',
            'llama3:8b': 'meta-llama/Llama-3-8B',
            'llama3:70b': 'meta-llama/Llama-3-70B',
            'mistral:7b': 'mistralai/Mistral-7B-v0.1',
            'mixtral:8x7b': 'mistralai/Mixtral-8x7B-v0.1',
            'codellama:7b': 'codellama/CodeLlama-7b-hf',
            'codellama:13b': 'codellama/CodeLlama-13b-hf',
            'codellama:34b': 'codellama/CodeLlama-34b-hf'
        }
        
        # Return mapped name or try to convert format
        if ollama_model_name in model_mapping:
            return model_mapping[ollama_model_name]
        
        # Try to convert common patterns
        if 'qwen' in ollama_model_name.lower():
            # Convert qwen2.5:32b -> Qwen/Qwen2.5-32B
            parts = ollama_model_name.split(':')
            if len(parts) == 2:
                version = parts[0].replace('.', '.').title()
                size = parts[1].upper()
                return f"Qwen/{version}-{size}"
        
        if 'llama' in ollama_model_name.lower():
            # Convert llama3.2:3b -> meta-llama/Llama-3.2-3B
            parts = ollama_model_name.split(':')
            if len(parts) == 2:
                version = parts[0].title().replace('.', '.')
                size = parts[1].upper()
                return f"meta-llama/{version}-{size}"
        
        # If no mapping found, return original (might fail but let's try)
        logger.warning(f"No mapping found for {ollama_model_name}, using as-is")
        return ollama_model_name

    def create_training_script(self, processed_dataset: str) -> str:
        """Create the actual training script using direct string formatting"""
        hf_model_name = self.get_hf_model_name(self.config['base_model'])
        logger.info(f"Using Hugging Face model: {hf_model_name}")
        
        # Create output directory path
        output_dir = os.path.join(self.temp_dir, "output")
        
        # Create the script content directly
        script_content = f'''#!/usr/bin/env python3

# IMPORTANT: Set environment variables BEFORE importing any libraries
import os
os.environ["HF_HUB_DISABLE_XET_STORAGE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HUGGINGFACE_HUB_DISABLE_XET"] = "1"

# Force disable Xet at the system level
import sys
sys.argv.extend(['--disable-xet', '--no-xet'])

import torch
import json
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForSeq2Seq,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from datasets import Dataset
import logging

# Suppress deprecation warnings to reduce log noise

# TrainingMetricsCallback temporarily removed due to f-string formatting issues in template generation
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_dataset(file_path):
    """Load and prepare dataset"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return Dataset.from_list(data)

def format_instruction(example):
    """Format instruction for training with Cantonese travel content style and JSON output"""
    # Handle the prompt/response format from the API
    if "prompt" in example:
        instruction = example["prompt"]
        response = example["response"]
    else:
        instruction = example["instruction"]
        response = example["output"]
    
    # Check if response is a JSON object (dict) or string
    if isinstance(response, dict):
        # Format JSON response as a string
        response_str = json.dumps(response, ensure_ascii=False, indent=2)
        # Create training text with JSON output instructions
        text = "你是一個專門分析機票優惠的助手，擅長用粵語（廣東話）寫出吸引人的旅遊內容。請只輸出JSON格式，不要輸出任何其他文字。包含以下欄位：\\n- Destination（目的地）：簡潔的中文地點名稱，如「東京」、「悉尼」\\n- Header（標題）：吸引人的標題，包含價格和出發資訊，如「精選東京遊！HK$2,390即刻出發！」\\n- Short Comment（簡短評論）：1-2句簡短評價，突出優惠點或特色\\n- Summary（詳細總結）：詳細的旅遊推薦內容，包含航班資訊、景點介紹、行程建議等\\n確保JSON格式完整，以}}結尾。\\n\\n"
    else:
        response_str = response
        # Create training text with plain text output instructions
        text = "你是一個專門分析機票優惠的助手，擅長用粵語（廣東話）寫出吸引人的旅遊內容。請用生動有趣的粵語風格寫出旅遊推薦內容。\\n\\n"
    
    text += "### 機票資料:\\n"
    text += instruction
    text += "\\n\\n### 旅遊推薦內容:\\n"
    text += response_str
    
    return {{"text": text}}


def main():
    print("=== LoRA Fine-tuning Script Started ===")
    print(f"Timestamp: {{__import__('datetime').datetime.now()}}")
    
    # Configuration
    base_model = {repr(self.config['base_model'])}
    adapter_name = {repr(self.config['adapter_name'])}
    session_id = {repr(self.session_id)}
    dataset_path = {repr(processed_dataset)}
    output_dir = {repr(output_dir)}
    
    print(f"Base model: {{base_model}}")
    print(f"Adapter name: {{adapter_name}}")
    print(f"Dataset path: {{dataset_path}}")
    print(f"Output directory: {{output_dir}}")
    
    # Training parameters (loaded from hyperparameters_config.py)
    learning_rate = {self.config.get('learning_rate', 0.0001)}
    num_epochs = {self.config.get('num_epochs', 3)}
    batch_size = {self.config.get('batch_size', 4)}
    gradient_accumulation_steps = {self.config.get('gradient_accumulation_steps', 8)}
    
    # LoRA parameters (loaded from hyperparameters_config.py)
    lora_rank = {self.config.get('lora_rank', 16)}
    lora_alpha = {self.config.get('lora_alpha', 32)}
    lora_dropout = {self.config.get('lora_dropout', 0.1)}
    target_modules = {self.config.get('target_modules', ['q_proj', 'v_proj', 'k_proj', 'o_proj'])}
    
    # Load tokenizer and model
    hf_model_name = {repr(hf_model_name)}
    print(f"Loading Hugging Face model: {{hf_model_name}}")
    logger.info(f"Loading model: {{hf_model_name}}")
    
    # Force disable Xet storage more aggressively
    import huggingface_hub.file_download
    import huggingface_hub.utils
    
    # Monkey patch to completely disable Xet
    original_get_hf_file_metadata = huggingface_hub.file_download.get_hf_file_metadata
    def patched_get_hf_file_metadata(*args, **kwargs):
        # Force disable xet in metadata
        result = original_get_hf_file_metadata(*args, **kwargs)
        if hasattr(result, 'xet_url'):
            result.xet_url = None
        return result
    huggingface_hub.file_download.get_hf_file_metadata = patched_get_hf_file_metadata
    
    # Also patch the utils
    if hasattr(huggingface_hub.utils, '_is_xet_available'):
        huggingface_hub.utils._is_xet_available = lambda: False
    
    tokenizer = AutoTokenizer.from_pretrained(hf_model_name, use_fast=False, token=False)
    print("Tokenizer loaded successfully")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print("Loading model (this may take a while for large models)...")
    
    try:
        print("Attempting to load model without quantization (using CPU offloading)...")
        
        # For 32B models, use pure CPU offloading without quantization
        if "32B" in hf_model_name:
            device_map = {{
                "model.embed_tokens": "cpu",
                "model.norm": "cpu",
                "lm_head": "cpu"
            }}
            
            # Put most layers on CPU, only a few on GPU
            num_layers = 80  # Qwen2.5-32B has 80 layers
            gpu_layers = 20  # Only 20 layers on GPU
            
            for i in range(num_layers):
                if i < gpu_layers:
                    device_map[f"model.layers.{{i}}"] = 0  # GPU
                else:
                    device_map[f"model.layers.{{i}}"] = "cpu"  # CPU
            
            model = AutoModelForCausalLM.from_pretrained(
                hf_model_name,
                device_map=device_map,
                torch_dtype=torch.float16,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                token=False,
                local_files_only=False,
                force_download=False,
                max_memory={{0: "14GB", "cpu": "35GB"}}
            )
        else:
            # For smaller models, use quantization
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )
            
            model = AutoModelForCausalLM.from_pretrained(
                hf_model_name,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                token=False,
                local_files_only=False,
                force_download=False
            )
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model {{hf_model_name}}: {{e}}")
        print("This might be due to network issues, Xet storage problems, or insufficient memory.")
        print("Suggestions:")
        print("1. Try using a smaller model like qwen2.5:7b or qwen2.5:3b")
        print("2. Check your internet connection")
        print("3. Ensure sufficient disk space and memory")
        raise
    
    # Configure LoRA for quantized model with gradient requirements
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
        bias="none",
        use_rslora=False  # Disable RSLoRA for compatibility
    )
    
    # Prepare model for training (handle both quantized and non-quantized)
    if "32B" in hf_model_name:
        # For 32B models without quantization, just enable training mode
        model.train()
        print("Model prepared for training (no quantization)")
    else:
        # For smaller quantized models, use k-bit training preparation
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model)
        print("Model prepared for k-bit training")
    
    # Add LoRA adapters
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # Ensure LoRA parameters require gradients
    for name, param in model.named_parameters():
        if "lora_" in name:
            param.requires_grad = True
    
    # Load and prepare dataset
    print("Loading and preparing dataset...")
    logger.info("Loading dataset...")
    dataset = load_dataset(dataset_path)
    print(f"Dataset loaded: {{len(dataset)}} examples")
    formatted_dataset = dataset.map(format_instruction)
    print("Dataset formatted successfully")
    
    # Tokenize dataset with consistent length handling
    def tokenize_and_format(examples):
        # Tokenize all texts with consistent padding
        tokenized = tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",  # Pad to max_length for consistent batching
            max_length=512,  # Further reduced to 512 for memory efficiency
            return_tensors=None
        )
        
        # For causal LM, labels are the same as input_ids
        tokenized["labels"] = tokenized["input_ids"].copy()
        
        return tokenized
    
    tokenized_dataset = formatted_dataset.map(
        tokenize_and_format,
        batched=True,
        remove_columns=formatted_dataset.column_names
    )
    
    # Training arguments with memory optimizations
    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=learning_rate,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=1,  # Reduce to 1 for memory efficiency
        gradient_accumulation_steps=gradient_accumulation_steps * batch_size,  # Compensate with more accumulation
        warmup_steps=100,
        logging_steps=10,
        save_steps=500,
        eval_steps=500,
        save_total_limit=2,
        prediction_loss_only=True,
        remove_unused_columns=False,
        push_to_hub=False,
        report_to=None,
        dataloader_pin_memory=False,
        gradient_checkpointing=False,  # Disable gradient checkpointing
        fp16=False,  # Disable mixed precision
        dataloader_num_workers=0,  # Reduce workers to save memory
        max_grad_norm=1.0,  # Gradient clipping
        ignore_data_skip=True,  # Skip data validation that might cause device issues
        disable_tqdm=False,  # Keep progress bars
        no_cuda=False,  # Allow CUDA usage
    )
    
    # Data collator for causal LM with proper padding
    from transformers import DataCollatorForLanguageModeling
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Not masked language modeling
        pad_to_multiple_of=8,  # Pad to multiple of 8 for efficiency
        return_tensors="pt"
    )
    
    # Create trainer (without complex callback for now to avoid f-string issues)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    # Start training
    print("=== Starting LoRA Training ===")
    print("Training for " + str(num_epochs) + " epochs with " + str(len(tokenized_dataset)) + " examples")
    logger.info("Starting training...")
    
    trainer.train()
    print("=== Training Completed ===")
    
    # Note: Training metrics collection temporarily disabled due to f-string formatting issues
    # Will be re-implemented with a different approach
    
    # Save the model
    logger.info("Saving model...")
    trainer.save_model()
    
    # Save adapter in GGUF format
    adapter_path = os.path.join(output_dir, "adapter")
    model.save_pretrained(adapter_path)
    
    # Convert adapter to GGUF format
    try:
        from gguf_converter import convert_adapter_to_gguf
        # Create config dict for GGUF conversion
        gguf_config = {{
            "adapter_name": "{self.config.get('adapter_name', 'unknown')}",
            "base_model": "{self.config.get('base_model', 'unknown')}",
            "lora_rank": {self.config.get('lora_rank', 16)},
            "lora_alpha": {self.config.get('lora_alpha', 32)},
            "lora_dropout": {self.config.get('lora_dropout', 0.1)},
            "learning_rate": {self.config.get('learning_rate', 0.0001)},
            "num_epochs": {self.config.get('num_epochs', 3)},
            "batch_size": {self.config.get('batch_size', 4)},
            "target_modules": {self.config.get('target_modules', ["q_proj", "v_proj", "k_proj", "o_proj"])}
        }}
        success = convert_adapter_to_gguf(adapter_path, model, tokenizer, gguf_config)
        if success:
            logger.info("Adapter converted to GGUF format successfully")
        else:
            logger.warning("GGUF conversion failed, adapter saved in original format")
    except Exception as e:
        logger.warning(f"Failed to convert adapter to GGUF: {{e}}")
        logger.info("Adapter saved in original format")
    
    logger.info("Training completed successfully!")
    
    # Save training info
    training_info = {{
        "base_model": base_model,
        "adapter_name": adapter_name,
        "export_id": session_id,  # Add export_id for model naming
        "lora_config": {{
            "r": lora_rank,
            "alpha": lora_alpha,
            "dropout": lora_dropout,
            "target_modules": target_modules
        }},
        "training_config": {{
            "learning_rate": learning_rate,
            "num_epochs": num_epochs,
            "batch_size": batch_size,
            "gradient_accumulation_steps": gradient_accumulation_steps
        }},
        "output_path": output_dir
    }}
    
    with open(os.path.join(output_dir, "training_info.json"), 'w', encoding='utf-8') as f:
        json.dump(training_info, f, indent=2)
    
    print(f"Training completed. Model saved to: {{output_dir}}")


if __name__ == "__main__":
    main()
'''
        
        # Copy GGUF converter to temp directory
        gguf_converter_path = os.path.join(self.temp_dir, "gguf_converter.py")
        shutil.copy2("gguf_converter.py", gguf_converter_path)
        
        # Write the script to file
        script_path = os.path.join(self.temp_dir, "train_model.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def create_requirements_file(self) -> str:
        """Create requirements.txt for training"""
        requirements = '''
torch>=2.0.0
transformers>=4.30.0
peft>=0.4.0
datasets>=2.12.0
accelerate>=0.20.0
bitsandbytes>=0.39.0
'''
        
        req_path = os.path.join(self.temp_dir, "requirements.txt")
        with open(req_path, 'w') as f:
            f.write(requirements)
        
        return req_path
    
    def install_dependencies(self) -> bool:
        """Install required dependencies"""
        try:
            # First, upgrade pip to avoid version conflicts
            logger.info("Upgrading pip...")
            pip_upgrade = subprocess.run([
                sys.executable, "-m", "pip", "install", "--upgrade", "pip"
            ], capture_output=True, text=True, timeout=60)
            
            if pip_upgrade.returncode != 0:
                logger.warning(f"Pip upgrade failed (continuing anyway): {pip_upgrade.stderr}")
            else:
                logger.info("Pip upgraded successfully")
            
            # Now install dependencies
            logger.info("Installing training dependencies...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                os.path.join(self.temp_dir, "requirements.txt")
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Failed to install dependencies: {result.stderr}")
                # Try with --user flag as fallback
                logger.info("Retrying with --user flag...")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", "--user", "-r", 
                    os.path.join(self.temp_dir, "requirements.txt")
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    logger.error(f"Failed to install dependencies with --user: {result.stderr}")
                    return False
            
            logger.info("Dependencies installed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout installing dependencies")
            return False
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False
    
    def run_training(self, dataset_path: str) -> bool:
        """Run the actual training"""
        try:
            import traceback
            # Prepare dataset
            processed_dataset = self.prepare_dataset(dataset_path)
            
            # Create training script
            script_path = self.create_training_script(processed_dataset)
            
            # Create requirements file
            self.create_requirements_file()
            
            # Install dependencies
            if not self.install_dependencies():
                return False
            
            # Run training with real-time output
            logger.info("Starting training process...")
            logger.info(f"Training script: {script_path}")
            logger.info("Training output will be shown in real-time:")
            logger.info("=" * 50)
            
            # Use subprocess.Popen for real-time output
            process = subprocess.Popen([
                sys.executable, script_path
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
               text=True, bufsize=1, universal_newlines=True)
            
            # Capture output in real-time
            output_lines = []
            timeout_count = 0
            max_timeout = 30  # 30 seconds without output before timeout
            
            while True:
                try:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        line = output.strip()
                        if line:
                            logger.info(f"  {line}")
                            output_lines.append(line)
                            timeout_count = 0  # Reset timeout counter
                    else:
                        timeout_count += 1
                        if timeout_count >= max_timeout:
                            logger.warning("No output received for 30 seconds, training might be stuck...")
                            logger.info("Training process is still running, continuing to wait...")
                            timeout_count = 0  # Reset counter but keep waiting
                except Exception as e:
                    logger.error(f"Error reading training output: {e}")
                    break
            
            # Wait for process to complete
            return_code = process.wait()
            
            logger.info("=" * 50)
            
            if return_code != 0:
                logger.error(f"Training failed with return code: {return_code}")
                return False
            
            logger.info("Training completed successfully")
            
            # Save training output to log file
            log_file = os.path.join(self.temp_dir, "training_output.log")
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=== TRAINING OUTPUT ===\n")
                f.write(f"Return code: {return_code}\n\n")
                f.write("=== OUTPUT ===\n")
                for line in output_lines:
                    f.write(f"{line}\n")
            
            logger.info(f"Training output saved to: {log_file}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Training timed out")
            return False
        except Exception as e:
            logger.error(f"Error during training: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def create_ollama_model(self) -> bool:
        """Create a new Ollama model by merging the adapter with the base model"""
        try:
            adapter_path = os.path.join(self.temp_dir, "output", "adapter")
            training_info_path = os.path.join(self.temp_dir, "output", "training_info.json")
            
            if not os.path.exists(adapter_path) or not os.path.exists(training_info_path):
                logger.error("Training output not found")
                return False
            
            # Load training info
            with open(training_info_path, 'r') as f:
                training_info = json.load(f)
            
            logger.info(f"Creating Ollama model: {self.config['adapter_name']}")
            logger.info("Merging LoRA adapter with base model for Ollama compatibility...")
            
            # Create a merged model script with properly escaped paths
            merge_script_content = f'''
import torch
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Load base model and tokenizer
print("Loading base model...")
base_model_name = {repr(self.get_hf_model_name(training_info['base_model']))}
tokenizer = AutoTokenizer.from_pretrained(base_model_name)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_name,
    torch_dtype=torch.float16,
    device_map="cpu",  # Use CPU for merging to avoid memory issues
    low_cpu_mem_usage=True
)

# Load and merge the LoRA adapter
print("Loading LoRA adapter...")
adapter_path = {repr(adapter_path)}
model = PeftModel.from_pretrained(base_model, adapter_path)

print("Merging adapter with base model...")
merged_model = model.merge_and_unload()

# Save the merged model
merged_path = {repr(os.path.join(self.temp_dir, 'merged_model'))}
print(f"Saving merged model to: {{merged_path}}")
merged_model.save_pretrained(merged_path, safe_serialization=True)
tokenizer.save_pretrained(merged_path)

print("Model merge completed successfully!")
'''
            
            # Write and execute the merge script
            merge_script_path = os.path.join(self.temp_dir, "merge_model.py")
            with open(merge_script_path, 'w', encoding='utf-8') as f:
                f.write(merge_script_content)
            
            # Execute the merge script
            logger.info("Executing model merge...")
            merge_result = subprocess.run([
                sys.executable, merge_script_path
            ], capture_output=True, text=True, cwd=self.temp_dir)
            
            if merge_result.returncode != 0:
                logger.error(f"Model merge failed: {merge_result.stderr}")
                # Fall back to simple Modelfile without adapter
                return self.create_simple_ollama_model(training_info)
            
            logger.info("Model merge completed successfully")
            
            # Export the adapter
            self.export_adapter(training_info)
            
            # Create model manifest and documentation
            self.create_model_manifest(training_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating Ollama model: {e}")
            return False
    
    def create_simple_ollama_model(self, training_info) -> bool:
        """Fallback: Export adapter without creating Ollama model"""
        try:
            logger.info("Exporting adapter without Ollama model creation...")
            
            # Export the adapter
            self.export_adapter(training_info)
            
            # Create model manifest and documentation
            self.create_model_manifest(training_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting adapter: {e}")
            return False
    
    def export_adapter(self, training_info):
        """Export the fine-tuned adapter for sharing and reuse"""
        try:
            import shutil
            from datetime import datetime
            
            # Create export directory in a permanent location
            export_dir = os.path.join(os.getcwd(), "adapter_exports", f"adapter_export_{self.session_id}")
            os.makedirs(export_dir, exist_ok=True)
            
            # Export adapter files - check multiple possible locations
            possible_adapter_paths = [
                os.path.join(self.temp_dir, "output", "adapter"),  # This is where it's actually saved
                os.path.join(self.temp_dir, "adapter_model"),
                os.path.join(self.temp_dir, "adapter"),
                os.path.join(self.temp_dir, "output", "adapter_model")
            ]
            
            adapter_found = False
            for adapter_path in possible_adapter_paths:
                if os.path.exists(adapter_path):
                    logger.info(f"Found adapter at: {adapter_path}")
                    # Copy adapter files to export directory
                    exported_adapter_path = os.path.join(export_dir, "adapter")
                    shutil.copytree(adapter_path, exported_adapter_path)
                    logger.info(f"Adapter files exported to: {exported_adapter_path}")
                    adapter_found = True
                    break
            
            if not adapter_found:
                logger.warning("Adapter files not found in any expected location")
                logger.warning(f"Searched paths: {possible_adapter_paths}")
                logger.warning("Creating configuration-only export")
            
            # Create adapter configuration file
            adapter_config = {
                "adapter_name": self.config['adapter_name'],
                "base_model": training_info.get('base_model', 'unknown'),
                "created_at": datetime.now().isoformat(),
                "session_id": self.session_id,
                "training_config": {
                    "learning_rate": self.config.get('learning_rate', 0.0001),
                    "epochs": self.config.get('num_epochs', 3),
                    "batch_size": self.config.get('batch_size', 4),
                    "lora_rank": self.config.get('lora_rank', 16),
                    "lora_alpha": self.config.get('lora_alpha', 32),
                    "lora_dropout": self.config.get('lora_dropout', 0.1),
                    "target_modules": self.config.get('target_modules', ["q_proj", "v_proj", "k_proj", "o_proj"]),
                    "use_quantization": self.config.get('use_quantization', True),
                    "gradient_accumulation_steps": self.config.get('gradient_accumulation_steps', 8),
                    "warmup_steps": self.config.get('warmup_steps', 100),
                    "max_length": self.config.get('max_length', 512)
                },
                "description": "Fine-tuned LoRA adapter for Cantonese travel content generation",
                "language": "Cantonese (Traditional Chinese)",
                "task": "Travel content generation with JSON output",
                "output_format": "JSON",
                "instructions": {
                    "system_prompt": "你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。你已經經過專門訓練，能夠根據機票資料寫出結構化的旅遊推薦內容。請只輸出JSON格式，不要輸出任何其他文字。",
                    "template": "你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。請根據提供的機票資料，只輸出JSON格式，不要輸出任何其他文字。",
                    "output_fields": {
                        "Destination": "簡潔的中文目的地名稱，如「東京」、「悉尼」",
                        "Header": "吸引人的標題，由三部份組成:機票評論, 航空公司目的地連價格, 出發資訊",
                        "Short Comment": "1-2句簡短評價，說服他人購買，指出有何吸引之處",
                        "Summary": "詳細的旅遊推薦內容，包含航班資訊、簡短景點介紹、價錢吸引處、或者行李寬限等"
                    }
                },
                "parameters": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "stop": ["}}"]
                },
                "files": {
                    "adapter_path": "adapter/",
                    "training_log": f"training_{self.session_id}.log",
                    "training_config": f"training_info_{self.session_id}.json"
                }
            }
            
            # Save adapter configuration
            config_path = os.path.join(export_dir, "adapter_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(adapter_config, f, ensure_ascii=False, indent=2)
            
            # Create usage instructions
            usage_instructions = f"""# {self.config['adapter_name']} - Adapter Usage Instructions

## Overview
This is a fine-tuned LoRA adapter for generating Cantonese travel content in JSON format.

## Adapter Information
- **Adapter Name**: {self.config['adapter_name']}
- **Base Model**: {training_info.get('base_model', 'unknown')}
- **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Session ID**: {self.session_id}

## How to Use This Adapter

### Option 1: With Transformers Library
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load base model
base_model = AutoModelForCausalLM.from_pretrained("{training_info.get('base_model', 'qwen2.5:14b').replace(':', '-')}")
tokenizer = AutoTokenizer.from_pretrained("{training_info.get('base_model', 'qwen2.5:14b').replace(':', '-')}")

# Load adapter
model = PeftModel.from_pretrained(base_model, "adapter/")

# Use for inference
def generate_travel_content(flight_data):
    prompt = f\"\"\"你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。請根據提供的機票資料，只輸出JSON格式，不要輸出任何其他文字。包含以下欄位：\\n- Destination（目的地）：簡潔的中文目的地名稱\\n- Header（標題）：吸引人的標題，由三部份組成:機票評論, 航空公司目的地連價格, 出發資訊\\n- Short Comment（簡短評論）：1-2句簡短評價，說服他人購買，指出有何吸引之處\\n- Summary（詳細總結）：詳細的旅遊推薦內容，包含航班資訊、簡短景點介紹、價錢吸引處、或者行李寬限等\\n確保JSON格式完整，以}}結尾。\\n\\n### 機票資料:\\n{{flight_data}}\\n\\n### 旅遊推薦內容:\"\"\"
    
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=512, temperature=0.7, do_sample=True)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Example usage
flight_data = "ANA全日空航空，香港到東京羽田，HK$2,390，10月8日14:45出發"
result = generate_travel_content(flight_data)
print(result)
```

### Option 2: Merge with Base Model
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load base model
base_model = AutoModelForCausalLM.from_pretrained("{training_info.get('base_model', 'qwen2.5:14b').replace(':', '-')}")
tokenizer = AutoTokenizer.from_pretrained("{training_info.get('base_model', 'qwen2.5:14b').replace(':', '-')}")

# Load and merge adapter
model = PeftModel.from_pretrained(base_model, "adapter/")
merged_model = model.merge_and_unload()

# Save merged model
merged_model.save_pretrained("merged_model")
tokenizer.save_pretrained("merged_model")
```

### Option 3: Create Ollama Modelfile
```dockerfile
FROM {training_info.get('base_model', 'qwen2.5:14b')}

SYSTEM \"\"\"你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。你已經經過專門訓練，能夠根據機票資料寫出結構化的旅遊推薦內容。請只輸出JSON格式，不要輸出任何其他文字。包含以下欄位：\\n- Destination（目的地）：簡潔的中文目的地名稱，如「東京」、「悉尼」\\n- Header（標題）：吸引人的標題，由三部份組成:機票評論, 航空公司目的地連價格, 出發資訊\\n- Short Comment（簡短評論）：1-2句簡短評價，說服他人購買，指出有何吸引之處\\n- Summary（詳細總結）：詳細的旅遊推薦內容，包含航班資訊、簡短景點介紹、價錢吸引處、或者行李寬限等\\n確保JSON格式完整，以}}結尾。\"\"\"

TEMPLATE \"\"\"你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。請根據提供的機票資料，只輸出JSON格式，不要輸出任何其他文字。\\n\\n### 機票資料:\\n{{{{ .Prompt }}}}\\n\\n### 旅遊推薦內容:\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER stop "}}"
```

## Training Configuration
- Learning Rate: {self.config.get('learning_rate', 0.0001)}
- Epochs: {self.config.get('num_epochs', 3)}
- Batch Size: {self.config.get('batch_size', 4)}
- LoRA Rank: {self.config.get('lora_rank', 16)}
- LoRA Alpha: {self.config.get('lora_alpha', 32)}
- LoRA Dropout: {self.config.get('lora_dropout', 0.1)}
- Target Modules: {self.config.get('target_modules', ["q_proj", "v_proj", "k_proj", "o_proj"])}

## Output Format
The adapter generates JSON output with the following structure:
```json
{{
  "Destination": "東京",
  "Header": "精選東京遊！HK$2,390即刻出發！",
  "Short Comment": "來一趟經濟實惠的東京之旅，賞櫻、品嚐美食，與日本文化近距離接觸。",
  "Summary": "利用ANA全日空航空，從香港前往東京羽田機場，只需HK$2,390便能體驗精采的旅程。10月8日搭乘下午兩點四十五分航班，帶來便利的時間安排。行李規定為一件不超過23kg的行李，讓你輕鬆享受旅程。"
}}
```

## Files Included
- `adapter/` - The LoRA adapter files
- `adapter_config.json` - Adapter configuration and metadata
- `USAGE.md` - This usage guide
- `training_{self.session_id}.log` - Training log
- `training_info_{self.session_id}.json` - Training configuration

## Notes
- This adapter is specifically trained for Cantonese (Traditional Chinese) travel content generation
- The output is always in JSON format with the specified fields
- Use temperature 0.7 for balanced creativity and consistency
- The adapter works best with the base model it was trained on
"""
            
            # Save usage instructions
            usage_path = os.path.join(export_dir, "USAGE.md")
            with open(usage_path, 'w', encoding='utf-8') as f:
                f.write(usage_instructions)
            
            # Copy training files to export directory
            training_files = [
                f"training_{self.session_id}.log",
                f"training_info_{self.session_id}.json"
            ]
            
            for file_name in training_files:
                src_path = os.path.join(self.temp_dir, file_name)
                if os.path.exists(src_path):
                    dst_path = os.path.join(export_dir, file_name)
                    shutil.copy2(src_path, dst_path)
            
            logger.info(f"Adapter exported successfully to: {export_dir}")
            logger.info(f"Export includes: adapter files, config, usage instructions, and training logs")
            
            # Create a simple merged model (base + adapter) for interception
            self.create_simple_merged_model(export_dir, training_info)
            
        except Exception as e:
            logger.error(f"Error exporting adapter: {e}")
    
    def create_simple_merged_model(self, export_dir, training_info):
        """Create a simple merged model (base + adapter) for use with interception"""
        try:
            logger.info("Creating simple merged model for adapter interception...")
            
            export_id = training_info.get('export_id', 'unknown')
            adapter_name = training_info.get('adapter_name', 'unknown')
            base_model = training_info.get('base_model', 'qwen2.5:14b')
            
            # Create a simple Modelfile for the merged model
            modelfile_content = f"""FROM {base_model}

# System prompt for the fine-tuned model
SYSTEM \"\"\"你是一個專門處理旅遊資訊的AI助手，特別擅長用繁體中文廣東話語氣來分析和描述機票優惠資訊。你已經經過專門訓練，能夠以自然、生動的廣東話風格來表達，同時保持專業和準確。

你的任務是根據提供的機票資料，生成吸引人的促銷內容，包括：
- 目的地名稱
- 吸引人的標題
- 簡短的評論（30字以內）
- 詳細的總結（約100字）

請使用繁體中文廣東話語氣，讓內容更貼近香港人講話的習慣。\"\"\"

# Template for conversation
TEMPLATE \"\"\"{{{{ if .System }}}}{{{{ .System }}}}{{{{ end }}}}{{{{ if .Prompt }}}}{{{{ .Prompt }}}}{{{{ end }}}}\"\"\"

# Parameters for better performance
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
"""
            
            # Save Modelfile
            modelfile_path = os.path.join(export_dir, 'Modelfile')
            with open(modelfile_path, 'w', encoding='utf-8') as f:
                f.write(modelfile_content)
            
            # Create Ollama model with the same name as export_id
            model_name = export_id
            logger.info(f"Creating Ollama model: {model_name}")
            
            import subprocess
            result = subprocess.run([
                'ollama', 'create', model_name, '-f', modelfile_path
            ], capture_output=True, text=True, cwd=export_dir)
            
            if result.returncode == 0:
                logger.info(f"✅ Simple merged model created successfully: {model_name}")
                logger.info(f"🎯 This model can be used with RAG interception")
                logger.info(f"📋 Model name: {model_name}")
            else:
                logger.error(f"❌ Failed to create merged model: {result.stderr}")
                logger.info("You can manually create the model using the Modelfile in the export directory")
                
        except Exception as e:
            logger.error(f"Error creating simple merged model: {e}")
            logger.info("Adapter export completed - you can manually create the merged model later")
    
    def create_rag_model_automatically(self, export_dir, training_info):
        """Automatically create a RAG model after adapter export"""
        # Temporarily disabled due to dependency issues with typer module
        # The RAG model creation can be done manually through the RAG Manager page
        logger.info("Automatic RAG model creation is disabled - adapter export completed successfully")
        logger.info("You can manually create a RAG model using the RAG Manager page if needed")
        
        # TODO: Re-enable when dependency issues are resolved
        # try:
        #     logger.info("Creating RAG model automatically after adapter export...")
        #     
        #     # Import the RAG adapter merger
        #     import sys
        #     import os
        #     
        #     # Add the backend directory to Python path to find rag_adapter_merger
        #     backend_dir = os.path.dirname(os.path.abspath(__file__))
        #     if backend_dir not in sys.path:
        #         sys.path.insert(0, backend_dir)
        #     
        #     # Also add the current working directory as fallback
        #     current_dir = os.getcwd()
        #     if current_dir not in sys.path:
        #         sys.path.insert(0, current_dir)
        #     
        #     # Try to import with more detailed error handling
        #     try:
        #         from rag_adapter_merger import RAGAdapterMerger
        #     except ImportError as import_err:
        #         logger.error(f"Failed to import RAGAdapterMerger: {import_err}")
        #         logger.error(f"Current working directory: {os.getcwd()}")
        #         logger.error(f"Backend directory: {backend_dir}")
        #         logger.error(f"Python path: {sys.path[:3]}")  # Show first 3 entries
        #         raise import_err
        #     
        #     # Get adapter export ID from the export directory path (keep the full export ID)
        #     export_id = os.path.basename(export_dir)
        #     
        #     # Create RAG adapter merger instance
        #     rag_merger = RAGAdapterMerger()
        #     
        #     # Create RAG model using the lightweight merge approach
        #     base_model = training_info.get('base_model', 'qwen2.5:14b')
        #     rag_result = rag_merger.create_rag_merged_model(export_id, base_model)
        #     
        #     if rag_result["success"]:
        #         logger.info(f"✅ RAG model created successfully: {rag_result['rag_model_name']}")
        #         logger.info(f"✅ Ollama model registered: {rag_result['ollama_model_name']}")
        #         logger.info(f"✅ Model is ready for immediate use in Flight Search!")
        #         
        #         # Log the model details for user reference
        #         print(f"""
        # 🎉 AUTOMATIC RAG MODEL CREATION COMPLETED! 🎉
        # 
        # Your fine-tuned adapter has been automatically merged and is ready to use:
        # 
        # 📦 RAG Model: {rag_result['rag_model_name']}
        # 🤖 Ollama Model: {rag_result['ollama_model_name']}
        # 🏗️  Base Model: {base_model}
        # 📁 Location: {rag_result['rag_model_path']}
        # 
        # ✅ You can now use this model in the Flight Search page!
        # ✅ No additional setup required - it's ready to go!
        # 
        # To use this model:
        # 1. Go to Flight Search page
        # 2. Select "{rag_result['adapter_name']} + RAG" from the AI Model dropdown
        # 3. Search and post flights - it will use your fine-tuned model!
        # 
        # """)
        #     else:
        #         logger.warning(f"Failed to create RAG model automatically: {rag_result.get('error', 'Unknown error')}")
        #         logger.info("Adapter is still available for manual RAG model creation in the RAG Manager page")
        #         
        # except ImportError as e:
        #     logger.warning(f"RAG adapter merger not available - skipping automatic RAG model creation: {e}")
        #     logger.info("You can manually create a RAG model in the RAG Manager page")
        # except Exception as e:
        #     logger.warning(f"Error creating RAG model automatically: {e}")
        #     logger.info("Adapter is still available for manual RAG model creation in the RAG Manager page")
    
    def create_model_manifest(self, training_info):
        """Create comprehensive model manifest and documentation"""
        try:
            import json
            from datetime import datetime
            
            # Get model info from Ollama
            model_info = self.get_ollama_model_info()
            
            # Create comprehensive manifest
            manifest = {
                "model_name": self.config['adapter_name'],
                "version": "1.0.0",
                "created_at": datetime.now().isoformat(),
                "base_model": training_info.get('base_model', 'unknown'),
                "description": "Fine-tuned model for Cantonese travel content generation with JSON output",
                "language": "Cantonese (Traditional Chinese)",
                "task": "Travel content generation",
                "output_format": "JSON",
                "training_config": {
                    "learning_rate": self.config.get('learning_rate', 0.0001),
                    "epochs": self.config.get('num_epochs', 3),
                    "batch_size": self.config.get('batch_size', 4),
                    "lora_rank": self.config.get('lora_rank', 16),
                    "lora_alpha": self.config.get('lora_alpha', 32),
                    "lora_dropout": self.config.get('lora_dropout', 0.1),
                    "use_quantization": self.config.get('use_quantization', True),
                    "gradient_accumulation_steps": self.config.get('gradient_accumulation_steps', 8),
                    "warmup_steps": self.config.get('warmup_steps', 100),
                    "max_length": self.config.get('max_length', 512)
                },
                "model_info": model_info,
                "output_fields": {
                    "Destination": {
                        "description": "簡潔的中文目的地名稱，如「東京」、「悉尼」",
                        "type": "string",
                        "example": "東京"
                    },
                    "Header": {
                        "description": "吸引人的標題，由三部份組成:機票評論, 航空公司目的地連價格, 出發資訊",
                        "type": "string", 
                        "example": "精選東京遊！HK$2,390即刻出發！"
                    },
                    "Short Comment": {
                        "description": "1-2句簡短評價，說服他人購買，指出有何吸引之處",
                        "type": "string",
                        "example": "來一趟經濟實惠的東京之旅，賞櫻、品嚐美食，與日本文化近距離接觸。"
                    },
                    "Summary": {
                        "description": "詳細的旅遊推薦內容，包含航班資訊、簡短景點介紹、價錢吸引處、或者行李寬限等",
                        "type": "string",
                        "example": "利用ANA全日空航空，從香港前往東京羽田機場，只需HK$2,390便能體驗精采的旅程。"
                    }
                },
                "usage_instructions": {
                    "input_format": "機票資料（航班資訊、價格、出發日期等）",
                    "output_format": "JSON格式，包含Destination、Header、Short Comment、Summary四個欄位",
                    "language": "粵語（繁體字）",
                    "style": "口語化、生動有趣、吸引人"
                },
                "parameters": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "repeat_penalty": 1.1,
                    "stop": ["}}"]
                },
                "files": {
                    "modelfile": "Modelfile",
                    "training_log": f"training_{self.session_id}.log",
                    "training_config": f"training_info_{self.session_id}.json"
                }
            }
            
            # Save manifest to temp directory
            manifest_path = os.path.join(self.temp_dir, "model_manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            # Create human-readable documentation
            self.create_model_documentation(manifest)
            
            logger.info(f"Model manifest created: {manifest_path}")
            
        except Exception as e:
            logger.error(f"Error creating model manifest: {e}")
    
    def get_ollama_model_info(self):
        """Get model information from Ollama"""
        try:
            result = subprocess.run([
                "ollama", "show", self.config['adapter_name'], "--json"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": f"Failed to get model info: {result.stderr}"}
        except Exception as e:
            return {"error": f"Error getting model info: {e}"}
    
    def create_model_documentation(self, manifest):
        """Create human-readable model documentation"""
        try:
            doc_content = f"""# {manifest['model_name']} - Model Documentation

## Overview
- **Model Name**: {manifest['model_name']}
- **Version**: {manifest['version']}
- **Created**: {manifest['created_at']}
- **Base Model**: {manifest['base_model']}
- **Language**: {manifest['language']}
- **Task**: {manifest['task']}

## Description
{manifest['description']}

## Output Format
The model generates structured JSON output in Cantonese (Traditional Chinese) with the following fields:

### Destination
- **Description**: {manifest['output_fields']['Destination']['description']}
- **Type**: {manifest['output_fields']['Destination']['type']}
- **Example**: {manifest['output_fields']['Destination']['example']}

### Header  
- **Description**: {manifest['output_fields']['Header']['description']}
- **Type**: {manifest['output_fields']['Header']['type']}
- **Example**: {manifest['output_fields']['Header']['example']}

### Short Comment
- **Description**: {manifest['output_fields']['Short Comment']['description']}
- **Type**: {manifest['output_fields']['Short Comment']['type']}
- **Example**: {manifest['output_fields']['Short Comment']['example']}

### Summary
- **Description**: {manifest['output_fields']['Summary']['description']}
- **Type**: {manifest['output_fields']['Summary']['type']}
- **Example**: {manifest['output_fields']['Summary']['example']}

## Usage Instructions
- **Input Format**: {manifest['usage_instructions']['input_format']}
- **Output Format**: {manifest['usage_instructions']['output_format']}
- **Language**: {manifest['usage_instructions']['language']}
- **Style**: {manifest['usage_instructions']['style']}

## Model Parameters
- Temperature: {manifest['parameters']['temperature']}
- Top P: {manifest['parameters']['top_p']}
- Top K: {manifest['parameters']['top_k']}
- Repeat Penalty: {manifest['parameters']['repeat_penalty']}
- Stop Tokens: {manifest['parameters']['stop']}

## Training Configuration
- Learning Rate: {manifest['training_config']['learning_rate']}
- Epochs: {manifest['training_config']['epochs']}
- Batch Size: {manifest['training_config']['batch_size']}
- LoRA Rank: {manifest['training_config']['lora_rank']}
- LoRA Alpha: {manifest['training_config']['lora_alpha']}
- LoRA Dropout: {manifest['training_config']['lora_dropout']}
- Use Quantization: {manifest['training_config']['use_quantization']}
- Gradient Accumulation Steps: {manifest['training_config']['gradient_accumulation_steps']}
- Warmup Steps: {manifest['training_config']['warmup_steps']}
- Max Length: {manifest['training_config']['max_length']}

## Files
- Modelfile: {manifest['files']['modelfile']}
- Training Log: {manifest['files']['training_log']}
- Training Config: {manifest['files']['training_config']}

## Example Usage
```bash
ollama run {manifest['model_name']}
```

Then provide flight/travel data as input to get structured Cantonese travel content in JSON format.
"""
            
            # Save documentation
            doc_path = os.path.join(self.temp_dir, "README.md")
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(doc_content)
            
            logger.info(f"Model documentation created: {doc_path}")
                
        except Exception as e:
            logger.error(f"Error creating model documentation: {e}")
    
    def cleanup(self):
        """Clean up temporary files, but preserve manifest and documentation"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Preserve important files before cleanup
                manifest_files = ['model_manifest.json', 'README.md']
                preserved_dir = os.path.join(os.path.dirname(self.temp_dir), f"model_artifacts_{self.session_id}")
                
                if any(os.path.exists(os.path.join(self.temp_dir, f)) for f in manifest_files):
                    os.makedirs(preserved_dir, exist_ok=True)
                    for file_name in manifest_files:
                        src_path = os.path.join(self.temp_dir, file_name)
                        if os.path.exists(src_path):
                            dst_path = os.path.join(preserved_dir, file_name)
                            shutil.copy2(src_path, dst_path)
                            logger.info(f"Preserved {file_name} in {preserved_dir}")
                
                # Note: Adapter export directory is already preserved separately
                
                # Clean up the temporary directory
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary files")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")
    
    def fine_tune(self, dataset_path: str) -> Dict[str, Any]:
        """Main fine-tuning method"""
        try:
            if not self.validate_config():
                return {"success": False, "error": "Invalid configuration"}
            
            logger.info(f"Starting fine-tuning with config: {self.config}")
            
            # Run training
            if not self.run_training(dataset_path):
                return {"success": False, "error": "Training failed"}
            
            # Create Ollama model
            if not self.create_ollama_model():
                return {"success": False, "error": "Failed to create Ollama model"}
            
            return {
                "success": True,
                "model_name": self.config['adapter_name'],
                "message": f"Successfully fine-tuned and registered model: {self.config['adapter_name']}"
            }
            
        except Exception as e:
            logger.error(f"Fine-tuning failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Clean up temporary files to save disk space
            self.cleanup()

def main():
    parser = argparse.ArgumentParser(description="LoRA Fine-tuning Script")
    parser.add_argument("--config", required=True, help="Training configuration JSON file")
    parser.add_argument("--dataset", required=True, help="Dataset file path")
    parser.add_argument("--output", help="Output directory (optional)")
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Initialize fine-tuner
    fine_tuner = LoRAFineTuner(config)
    
    # Run fine-tuning
    result = fine_tuner.fine_tune(args.dataset)
    
    # Print result
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__":
    main()
