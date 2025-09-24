#!/usr/bin/env python3
"""
Hyperparameters Configuration for Fine-tuning
This file contains all the training hyperparameters that are controlled by the system administrator.
Users can no longer modify these parameters through the UI.
"""

# ============================================================================
# TRAINING HYPERPARAMETERS
# ============================================================================

# Learning Parameters
LEARNING_RATE = 0.0001
NUM_EPOCHS = 5
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 8

# LoRA Parameters
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.1
TARGET_MODULES = ['q_proj', 'v_proj', 'k_proj', 'o_proj']

# Advanced Training Parameters
WARMUP_STEPS = 100
LOGGING_STEPS = 10
SAVE_STEPS = 500
EVAL_STEPS = 500
SAVE_TOTAL_LIMIT = 2
MAX_GRAD_NORM = 1.0

# Memory Optimization Parameters
PER_DEVICE_TRAIN_BATCH_SIZE = 1  # Reduced for memory efficiency
MAX_LENGTH = 512  # Maximum sequence length for tokenization
PAD_TO_MULTIPLE_OF = 8  # Padding for efficiency

# Model Loading Parameters
USE_4BIT_QUANTIZATION = True
BNB_4BIT_USE_DOUBLE_QUANT = True
BNB_4BIT_QUANT_TYPE = "nf4"
BNB_4BIT_COMPUTE_DTYPE = "float16"

# For 32B models - CPU offloading configuration
GPU_LAYERS_32B = 20  # Number of layers to keep on GPU for 32B models
TOTAL_LAYERS_32B = 80  # Total layers in 32B models

# ============================================================================
# MODEL-SPECIFIC CONFIGURATIONS
# ============================================================================

# Different configurations for different model sizes
MODEL_CONFIGS = {
    # Small models (1B-3B)
    'small': {
        'learning_rate': 0.0002,
        'num_epochs': 3,
        'batch_size': 8,
        'lora_rank': 8,
        'lora_alpha': 16,
        'use_quantization': True
    },
    
    # Medium models (7B-14B)
    'medium': {
        'learning_rate': 0.0001,
        'num_epochs': 3,
        'batch_size': 4,
        'lora_rank': 16,
        'lora_alpha': 32,
        'use_quantization': True
    },
    
    # Large models (32B+)
    'large': {
        'learning_rate': 0.00005,
        'num_epochs': 2,
        'batch_size': 2,
        'lora_rank': 32,
        'lora_alpha': 64,
        'use_quantization': False,  # Use CPU offloading instead
        'gpu_layers': GPU_LAYERS_32B
    }
}

def get_model_size_category(model_name: str) -> str:
    """
    Determine model size category based on model name
    """
    model_name_lower = model_name.lower()
    
    if any(size in model_name_lower for size in ['1b', '1.5b', '3b']):
        return 'small'
    elif any(size in model_name_lower for size in ['7b', '8b', '14b']):
        return 'medium'
    elif any(size in model_name_lower for size in ['32b', '70b']):
        return 'large'
    else:
        # Default to medium for unknown models
        return 'medium'

def get_training_config(base_model: str) -> dict:
    """
    Get training configuration based on the base model
    """
    model_category = get_model_size_category(base_model)
    config = MODEL_CONFIGS[model_category].copy()
    
    # Add common parameters
    config.update({
        'gradient_accumulation_steps': GRADIENT_ACCUMULATION_STEPS,
        'lora_dropout': LORA_DROPOUT,
        'target_modules': TARGET_MODULES.copy(),
        'warmup_steps': WARMUP_STEPS,
        'logging_steps': LOGGING_STEPS,
        'save_steps': SAVE_STEPS,
        'eval_steps': EVAL_STEPS,
        'save_total_limit': SAVE_TOTAL_LIMIT,
        'max_grad_norm': MAX_GRAD_NORM,
        'per_device_train_batch_size': PER_DEVICE_TRAIN_BATCH_SIZE,
        'max_length': MAX_LENGTH,
        'pad_to_multiple_of': PAD_TO_MULTIPLE_OF,
    })
    
    # Add quantization parameters if using quantization
    if config.get('use_quantization', True):
        config.update({
            'use_4bit_quantization': USE_4BIT_QUANTIZATION,
            'bnb_4bit_use_double_quant': BNB_4BIT_USE_DOUBLE_QUANT,
            'bnb_4bit_quant_type': BNB_4BIT_QUANT_TYPE,
            'bnb_4bit_compute_dtype': BNB_4BIT_COMPUTE_DTYPE,
        })
    
    return config

# ============================================================================
# VALIDATION CONSTRAINTS
# ============================================================================

# Validation ranges (for server-side validation)
VALIDATION_RANGES = {
    'learning_rate': (0.00001, 0.01),
    'num_epochs': (1, 10),
    'batch_size': (1, 16),
    'lora_rank': (4, 64),
    'lora_alpha': (8, 128),
    'lora_dropout': (0.0, 0.5),
    'gradient_accumulation_steps': (1, 32)
}

def validate_hyperparameters(config: dict) -> tuple[bool, list[str]]:
    """
    Validate hyperparameters against allowed ranges
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    for param, (min_val, max_val) in VALIDATION_RANGES.items():
        if param in config:
            value = config[param]
            if not (min_val <= value <= max_val):
                errors.append(f"{param} must be between {min_val} and {max_val}, got {value}")
    
    return len(errors) == 0, errors

# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

def get_config_summary() -> str:
    """
    Get a summary of the current hyperparameter configuration
    """
    return f"""
Fine-tuning Hyperparameters Configuration:
==========================================

Default Configuration:
- Learning Rate: {LEARNING_RATE}
- Epochs: {NUM_EPOCHS}
- Batch Size: {BATCH_SIZE}
- LoRA Rank: {LORA_RANK}
- LoRA Alpha: {LORA_ALPHA}
- LoRA Dropout: {LORA_DROPOUT}

Model-Specific Configurations:
{chr(10).join([f"- {size}: {config}" for size, config in MODEL_CONFIGS.items()])}

These parameters are controlled by the system administrator and cannot be modified through the UI.
To change these settings, modify this configuration file and restart the fine-tuning service.
"""

if __name__ == "__main__":
    print(get_config_summary())
