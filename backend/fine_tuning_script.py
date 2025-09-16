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
            with open(dataset_path, 'r', encoding='utf-8') as f:
                if dataset_path.endswith('.json'):
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError("JSON file must contain an array of training examples")
                elif dataset_path.endswith('.jsonl'):
                    data = []
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
                else:
                    raise ValueError("Unsupported file format. Use .json or .jsonl")
            
            # Convert to training format
            training_data = []
            for item in data:
                if 'prompt' not in item or 'response' not in item:
                    logger.warning(f"Skipping item missing prompt/response: {item}")
                    continue
                    
                training_example = {
                    "instruction": item['prompt'],
                    "input": "",
                    "output": item['response']
                }
                training_data.append(training_example)
            
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
            'qwen2.5:7b': 'Qwen/Qwen2.5-7B',
            'qwen2.5:3b': 'Qwen/Qwen2.5-3B',
            'qwen2.5:1.5b': 'Qwen/Qwen2.5-1.5B',
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

    def create_training_script(self, dataset_path: str) -> str:
        """Create the actual training script"""
        hf_model_name = self.get_hf_model_name(self.config['base_model'])
        logger.info(f"Using Hugging Face model: {hf_model_name}")
        
        script_content = f'''
import torch
import json
import os
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from datasets import Dataset
import logging

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
    if example["input"]:
        prompt = f"""Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{{example["instruction"]}}

### Input:
{{example["input"]}}

### Response:"""
    else:
        prompt = f"""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{{example["instruction"]}}

### Response:"""
    
    return {{
        "prompt": prompt,
        "completion": example["output"]
    }}

def tokenize_function(examples, tokenizer, max_length=512):
    """Tokenize the examples"""
    model_inputs = tokenizer(
        examples["prompt"],
        max_length=max_length,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    
    labels = tokenizer(
        examples["completion"],
        max_length=max_length,
        padding=True,
        truncation=True,
        return_tensors="pt"
    )
    
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

def main():
    # Configuration
    base_model = "{self.config['base_model']}"
    adapter_name = "{self.config['adapter_name']}"
    dataset_path = "{dataset_path}"
    output_dir = "{self.temp_dir}/output"
    
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
    hf_model_name = "{hf_model_name}"
    logger.info(f"Loading model: {{hf_model_name}}")
    tokenizer = AutoTokenizer.from_pretrained(hf_model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        hf_model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Configure LoRA
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    # Load and prepare dataset
    logger.info("Loading dataset...")
    dataset = load_dataset(dataset_path)
    formatted_dataset = dataset.map(format_instruction)
    
    # Tokenize dataset
    tokenized_dataset = formatted_dataset.map(
        lambda x: tokenize_function(x, tokenizer),
        batched=True
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=learning_rate,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
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
    )
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
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
    logger.info("Starting training...")
    trainer.train()
    
    # Save the model
    logger.info("Saving model...")
    trainer.save_model()
    
    # Save adapter
    model.save_pretrained(f"{{output_dir}}/adapter")
    
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
    
    with open(f"{{output_dir}}/training_info.json", 'w') as f:
        json.dump(training_info, f, indent=2)
    
    print(f"Training completed. Model saved to: {{output_dir}}")

if __name__ == "__main__":
    main()
'''
        
        script_path = os.path.join(self.temp_dir, "train_model.py")
        with open(script_path, 'w') as f:
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
            logger.info("Installing training dependencies...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", 
                os.path.join(self.temp_dir, "requirements.txt")
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Failed to install dependencies: {result.stderr}")
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
            
            # Run training
            logger.info("Starting training process...")
            result = subprocess.run([
                sys.executable, script_path
            ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            if result.returncode != 0:
                logger.error(f"Training failed: {result.stderr}")
                return False
            
            logger.info("Training completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Training timed out")
            return False
        except Exception as e:
            logger.error(f"Error during training: {e}")
            return False
    
    def create_ollama_model(self) -> bool:
        """Create a new Ollama model from the fine-tuned adapter"""
        try:
            adapter_path = os.path.join(self.temp_dir, "output", "adapter")
            training_info_path = os.path.join(self.temp_dir, "output", "training_info.json")
            
            if not os.path.exists(adapter_path) or not os.path.exists(training_info_path):
                logger.error("Training output not found")
                return False
            
            # Load training info
            with open(training_info_path, 'r') as f:
                training_info = json.load(f)
            
            # Create Modelfile for Ollama
            modelfile_content = f'''FROM {training_info['base_model']}

# LoRA adapter configuration
ADAPTER {adapter_path}

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
            
            modelfile_path = os.path.join(self.temp_dir, "Modelfile")
            with open(modelfile_path, 'w') as f:
                f.write(modelfile_content)
            
            # Create model in Ollama (works with Docker)
            logger.info(f"Creating Ollama model: {self.config['adapter_name']}")
            
            # Try to use ollama command first
            result = subprocess.run([
                "ollama", "create", self.config['adapter_name'], "-f", modelfile_path
            ], capture_output=True, text=True)
            
            # If ollama command fails, try via Docker exec
            if result.returncode != 0:
                logger.info("ollama command failed, trying Docker exec...")
                docker_result = subprocess.run([
                    "docker", "exec", "ollama", "ollama", "create", 
                    self.config['adapter_name'], "-f", "/tmp/Modelfile"
                ], capture_output=True, text=True)
                
                # Copy modelfile to Docker container
                if docker_result.returncode != 0:
                    logger.info("Copying Modelfile to Docker container...")
                    copy_result = subprocess.run([
                        "docker", "cp", modelfile_path, f"ollama:/tmp/Modelfile"
                    ], capture_output=True, text=True)
                    
                    if copy_result.returncode == 0:
                        # Try again with copied file
                        docker_result = subprocess.run([
                            "docker", "exec", "ollama", "ollama", "create", 
                            self.config['adapter_name'], "-f", "/tmp/Modelfile"
                        ], capture_output=True, text=True)
                        result = docker_result
            
            if result.returncode != 0:
                logger.error(f"Failed to create Ollama model: {result.stderr}")
                return False
            
            logger.info(f"Successfully created Ollama model: {self.config['adapter_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Ollama model: {e}")
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
