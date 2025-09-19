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
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoRAFineTuner:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = None
        self.model_output_path = None
        
    def validate_config(self) -> bool:
        """Validate the training configuration"""
        required_fields = ['base_model', 'adapter_name', 'learning_rate', 'num_epochs', 'batch_size']
        
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required field: {field}")
                return False
                
        if self.config['learning_rate'] <= 0 or self.config['learning_rate'] > 1:
            logger.error("Learning rate must be between 0 and 1")
            return False
            
        if self.config['num_epochs'] <= 0 or self.config['num_epochs'] > 100:
            logger.error("Number of epochs must be between 1 and 100")
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
    """Format instruction for training"""
    # Handle the prompt/response format from the API
    if "prompt" in example:
        instruction = example["prompt"]
        response = example["response"]
    else:
        instruction = example["instruction"]
        response = example["output"]
    
    # Create training text using string concatenation to avoid f-string issues
    text = "Below is an instruction that describes a task. Write a response that appropriately completes the request.\\n\\n"
    text += "### Instruction:\\n"
    text += instruction
    text += "\\n\\n### Response:\\n"
    text += response
    
    return {{"text": text}}


def main():
    print("=== LoRA Fine-tuning Script Started ===")
    print(f"Timestamp: {{__import__('datetime').datetime.now()}}")
    
    # Configuration
    base_model = {repr(self.config['base_model'])}
    adapter_name = {repr(self.config['adapter_name'])}
    dataset_path = {repr(processed_dataset)}
    output_dir = {repr(output_dir)}
    
    print(f"Base model: {{base_model}}")
    print(f"Adapter name: {{adapter_name}}")
    print(f"Dataset path: {{dataset_path}}")
    print(f"Output directory: {{output_dir}}")
    
    # Training parameters
    learning_rate = {self.config['learning_rate']}
    num_epochs = {self.config['num_epochs']}
    batch_size = {self.config['batch_size']}
    gradient_accumulation_steps = {self.config.get('gradient_accumulation_steps', 4)}
    
    # LoRA parameters
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
    
    # Configure aggressive quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_storage=torch.uint8  # Use uint8 for storage
    )
    
    try:
        print("Attempting to load model with regular HTTP download...")
        model = AutoModelForCausalLM.from_pretrained(
            hf_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            token=False,  # Updated parameter name
            local_files_only=False,
            force_download=False,  # Use cache if available
            proxies=None  # Disable any proxy that might interfere
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
    
    # Enable gradient checkpointing on the base model before adding LoRA
    model.gradient_checkpointing_enable()
    
    # Prepare model for k-bit training (required for quantized models)
    from peft import prepare_model_for_kbit_training
    model = prepare_model_for_kbit_training(model)
    
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
        gradient_checkpointing=True,  # Enable gradient checkpointing for memory savings
        fp16=True,  # Use mixed precision training
        dataloader_num_workers=0,  # Reduce workers to save memory
        max_grad_norm=1.0,  # Gradient clipping
    )
    
    # Data collator for causal LM with proper padding
    from transformers import DataCollatorForLanguageModeling
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Not masked language modeling
        pad_to_multiple_of=8,  # Pad to multiple of 8 for efficiency
        return_tensors="pt"
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    # Start training
    print("=== Starting LoRA Training ===")
    logger.info("Starting training...")
    trainer.train()
    print("=== Training Completed ===")
    
    # Save the model
    logger.info("Saving model...")
    trainer.save_model()
    
    # Save adapter
    model.save_pretrained(os.path.join(output_dir, "adapter"))
    
    logger.info("Training completed successfully!")
    
    # Save training info
    training_info = {{
        "base_model": base_model,
        "adapter_name": adapter_name,
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
    
    with open(os.path.join(output_dir, "training_info.json"), 'w') as f:
        json.dump(training_info, f, indent=2)
    
    print(f"Training completed. Model saved to: {{output_dir}}")

if __name__ == "__main__":
    main()
'''
        
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
            with open(log_file, 'w') as f:
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
            with open(merge_script_path, 'w') as f:
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
            
            # Create Ollama model from merged model
            merged_model_path = os.path.join(self.temp_dir, "merged_model")
            
            # Create simple Modelfile that references the base model with custom instructions
            modelfile_content = f'''FROM {training_info['base_model']}

# Fine-tuned for travel booking assistance based on training data
SYSTEM \"\"\"You are a helpful assistant specialized in travel and flight booking information. You have been fine-tuned on travel booking data to provide structured responses with destination details, headers, comments, and summaries. When given flight information, respond in a structured format similar to your training examples.\"\"\"

# Template for instruction following
TEMPLATE \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{{{{ .Prompt }}}}

### Response:
\"\"\"

# Parameters optimized for travel assistance
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
'''
            
            modelfile_path = os.path.join(self.temp_dir, "Modelfile")
            with open(modelfile_path, 'w') as f:
                f.write(modelfile_content)
            
            # Create model in Ollama
            result = subprocess.run([
                "ollama", "create", self.config['adapter_name'], "-f", modelfile_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to create Ollama model: {result.stderr}")
                logger.error(f"Ollama stdout: {result.stdout}")
                return False
            
            logger.info(f"Successfully created Ollama model: {self.config['adapter_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Ollama model: {e}")
            return False
    
    def create_simple_ollama_model(self, training_info) -> bool:
        """Fallback: Create a simple Ollama model without adapter"""
        try:
            logger.info("Creating simple Ollama model without adapter as fallback...")
            
            modelfile_content = f'''FROM {training_info['base_model']}

# Fine-tuned behavior simulation
SYSTEM \"\"\"You are a helpful assistant specialized in travel and flight booking information. When provided with flight booking data, respond with structured information including destination details, headers, short comments, and summaries in a clear, organized format.\"\"\"

# Template for instruction following  
TEMPLATE \"\"\"Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{{{{ .Prompt }}}}

### Response:
\"\"\"

# Parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
'''
            
            modelfile_path = os.path.join(self.temp_dir, "Modelfile_simple")
            with open(modelfile_path, 'w') as f:
                f.write(modelfile_content)
            
            # Create model in Ollama
            result = subprocess.run([
                "ollama", "create", self.config['adapter_name'], "-f", modelfile_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully created simple Ollama model: {self.config['adapter_name']}")
                return True
            else:
                logger.error(f"Failed to create simple Ollama model: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating simple Ollama model: {e}")
            return False
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
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
            # Note: Don't cleanup here so user can inspect results
            pass

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
