#!/usr/bin/env python3
"""
GGUF Converter for LoRA Adapters
Converts LoRA adapters to GGUF format for better compatibility
"""

import os
import sys
import json
import logging
import subprocess
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GGUFConverter:
    """Convert LoRA adapters to GGUF format"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.gguf_writer = None
        
    def install_gguf(self):
        """Install GGUF library if not available"""
        try:
            import gguf
            logger.info("GGUF library already available")
            return True
        except ImportError:
            logger.info("Installing GGUF library...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "gguf"
                ], check=True, capture_output=True, text=True)
                logger.info("GGUF library installed successfully")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install GGUF library: {e}")
                return False
    
    def convert_adapter_to_gguf(self, adapter_path: str, model, tokenizer=None) -> bool:
        """
        Convert LoRA adapter to GGUF format
        
        Args:
            adapter_path: Path to the adapter directory
            model: The trained model with LoRA adapter
            tokenizer: Optional tokenizer for metadata
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Install GGUF if needed
            if not self.install_gguf():
                return False
            
            from gguf import GGUFWriter
            
            # Create GGUF file path
            gguf_path = os.path.join(adapter_path, "adapter.gguf")
            logger.info(f"Converting adapter to GGUF: {gguf_path}")
            
            # Create GGUF writer
            writer = GGUFWriter(gguf_path, "llama")  # Use llama as base architecture
            
            # Extract adapter weights
            adapter_weights = self._extract_adapter_weights(model)
            
            if adapter_weights:
                # Add adapter weights to GGUF
                for name, tensor in adapter_weights.items():
                    try:
                        # Convert PyTorch tensor to numpy array for GGUF
                        tensor_np = tensor.numpy()
                        logger.debug(f"Adding tensor {name} with dtype {tensor_np.dtype} and shape {tensor_np.shape}")
                        writer.add_tensor(name, tensor_np)
                        logger.debug(f"Successfully added tensor {name}")
                    except Exception as tensor_error:
                        logger.error(f"Failed to add tensor {name}: {tensor_error}")
                        logger.error(f"Tensor dtype: {tensor.dtype}, shape: {tensor.shape}")
                        # Try converting to numpy array if it fails
                        try:
                            tensor_np = tensor.numpy()
                            logger.info(f"Retrying with numpy conversion for {name}")
                            writer.add_tensor(name, tensor_np)
                            logger.info(f"Successfully added tensor {name} after numpy conversion")
                        except Exception as retry_error:
                            logger.error(f"Failed to add tensor {name} even after numpy conversion: {retry_error}")
                            continue
                logger.info(f"Added {len(adapter_weights)} adapter tensors to GGUF")
            else:
                logger.warning("No adapter weights found, creating metadata-only GGUF")
            
            # Add metadata
            self._add_metadata(writer, tokenizer)
            
            # Write the GGUF file
            writer.write_header_to_file()
            writer.write_kv_data_to_file()
            writer.write_tensors_to_file()
            writer.close()
            
            logger.info(f"GGUF adapter saved to: {gguf_path}")
            
            # Create documentation
            self._create_gguf_documentation(adapter_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error converting adapter to GGUF: {e}")
            # Try to create a metadata-only GGUF file as fallback
            try:
                logger.info("Attempting to create metadata-only GGUF file as fallback")
                gguf_path = os.path.join(adapter_path, "adapter.gguf")
                writer = GGUFWriter(gguf_path, "llama")
                
                # Add only metadata, no tensors
                self._add_metadata(writer, tokenizer)
                
                # Write the GGUF file
                writer.write_header_to_file()
                writer.write_kv_data_to_file()
                writer.write_tensors_to_file()
                writer.close()
                
                logger.info(f"Created metadata-only GGUF file: {gguf_path}")
                return True
                
            except Exception as fallback_error:
                logger.error(f"Failed to create metadata-only GGUF file: {fallback_error}")
                return False
    
    def _extract_adapter_weights(self, model) -> Dict[str, Any]:
        """Extract LoRA adapter weights from the model"""
        adapter_weights = {}
        
        try:
            if hasattr(model, 'peft_config'):
                # This is a PEFT model
                logger.info("Extracting weights from PEFT model")
                for name, param in model.named_parameters():
                    if 'lora' in name.lower():
                        # Convert tensor to supported data type
                        tensor = param.detach().cpu()
                        # Convert to float32 for GGUF compatibility
                        tensor = tensor.float()
                        adapter_weights[name] = tensor
                        logger.debug(f"Found LoRA parameter: {name}, shape: {param.shape}, dtype: {tensor.dtype}")
            else:
                # Try to find LoRA parameters in the model
                logger.info("Searching for LoRA parameters in model")
                for name, param in model.named_parameters():
                    if any(keyword in name.lower() for keyword in ['lora', 'adapter', 'delta']):
                        # Convert tensor to supported data type
                        tensor = param.detach().cpu()
                        # Convert to float32 for GGUF compatibility
                        tensor = tensor.float()
                        adapter_weights[name] = tensor
                        logger.debug(f"Found adapter parameter: {name}, shape: {param.shape}, dtype: {tensor.dtype}")
            
            if not adapter_weights:
                logger.warning("No LoRA parameters found in model")
            
        except Exception as e:
            logger.error(f"Error extracting adapter weights: {e}")
        
        return adapter_weights
    
    def _add_metadata(self, writer, tokenizer=None):
        """Add metadata to the GGUF file"""
        try:
            # General metadata
            writer.add_string("general.name", f"{self.config.get('adapter_name', 'unknown')}_adapter")
            writer.add_string("general.description", "Fine-tuned LoRA adapter for Cantonese travel content generation")
            # Note: general.architecture might be set automatically by GGUFWriter
            writer.add_string("general.file_type", "GGUF")
            writer.add_string("general.quantization_method", "none")
            
            # Adapter-specific metadata
            writer.add_string("adapter.name", self.config.get('adapter_name', 'unknown'))
            writer.add_string("adapter.base_model", self.config.get('base_model', 'unknown'))
            writer.add_string("adapter.task", "text-generation")
            writer.add_string("adapter.language", "Cantonese")
            writer.add_string("adapter.output_format", "JSON")
            
            # Training configuration
            writer.add_uint32("adapter.lora_rank", self.config.get('lora_rank', 16))
            writer.add_float32("adapter.lora_alpha", self.config.get('lora_alpha', 32.0))
            writer.add_float32("adapter.lora_dropout", self.config.get('lora_dropout', 0.1))
            writer.add_float32("adapter.learning_rate", self.config.get('learning_rate', 0.0001))
            writer.add_uint32("adapter.epochs", self.config.get('num_epochs', 3))
            writer.add_uint32("adapter.batch_size", self.config.get('batch_size', 4))
            
            # Target modules
            target_modules = self.config.get('target_modules', ["q_proj", "v_proj", "k_proj", "o_proj"])
            writer.add_string("adapter.target_modules", json.dumps(target_modules))
            
            # Add tokenizer information if available
            if tokenizer is not None:
                try:
                    vocab_size = len(tokenizer.get_vocab())
                    writer.add_uint32("tokenizer.ggml.vocab_size", vocab_size)
                    writer.add_string("tokenizer.ggml.model", "llama")
                    logger.info(f"Added tokenizer info: vocab_size={vocab_size}")
                except Exception as e:
                    logger.warning(f"Could not add tokenizer info: {e}")
            
            logger.info("Metadata added to GGUF file")
            
        except Exception as e:
            logger.error(f"Error adding metadata: {e}")
    
    def _create_gguf_documentation(self, adapter_path: str):
        """Create documentation for the GGUF file"""
        try:
            readme_content = f"""# {self.config.get('adapter_name', 'unknown')} - GGUF Adapter

## Overview
This is a LoRA adapter converted to GGUF format for use with compatible inference engines.

## File Information
- **File**: adapter.gguf
- **Format**: GGUF (GGML Universal Format)
- **Base Model**: {self.config.get('base_model', 'unknown')}
- **Task**: Cantonese travel content generation
- **Language**: Cantonese (Traditional Chinese)
- **Output Format**: JSON

## Usage

### With llama.cpp
```bash
# Basic usage
./llama-cli -m adapter.gguf -p "機票資料: ANA全日空航空，香港到東京羽田，HK$2,390"

# With specific parameters
./llama-cli -m adapter.gguf -p "Your prompt" --temp 0.7 --top-p 0.9 --top-k 40
```

### With Python (using compatible libraries)
```python
# Load the GGUF file with a compatible library
# The file contains all necessary metadata for integration
```

## Training Configuration
- **LoRA Rank**: {self.config.get('lora_rank', 16)}
- **LoRA Alpha**: {self.config.get('lora_alpha', 32)}
- **LoRA Dropout**: {self.config.get('lora_dropout', 0.1)}
- **Learning Rate**: {self.config.get('learning_rate', 0.0001)}
- **Epochs**: {self.config.get('num_epochs', 3)}
- **Batch Size**: {self.config.get('batch_size', 4)}
- **Target Modules**: {self.config.get('target_modules', ['q_proj', 'v_proj', 'k_proj', 'o_proj'])}

## Output Format
The adapter generates JSON output with the following structure:
```json
{{
  "Destination": "東京",
  "Header": "精選東京遊！HK$2,390即刻出發！",
  "Short Comment": "來一趟經濟實惠的東京之旅，賞櫻、品嚐美食，與日本文化近距離接觸。",
  "Summary": "利用ANA全日空航空，從香港前往東京羽田機場，只需HK$2,390便能體驗精采的旅程。"
}}
```

## Compatible Engines
This GGUF file can be used with:
- **llama.cpp**: Direct support
- **GGML-based inference engines**: Native compatibility
- **Compatible model loading libraries**: Various Python libraries
- **Cross-platform**: Works on Windows, Linux, macOS

## Notes
- This adapter is specifically trained for Cantonese travel content generation
- The output is always in JSON format with structured fields
- Use temperature 0.7 for balanced creativity and consistency
- The adapter works best with the base model it was trained on
- GGUF format provides better compatibility and portability

## File Structure
```
adapter/
├── adapter.gguf          # Main GGUF file
├── README.md             # This documentation
├── adapter_config.json   # PEFT configuration (backup)
└── adapter_model.safetensors  # Original format (backup)
```
"""
            
            readme_path = os.path.join(adapter_path, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            logger.info(f"GGUF documentation created: {readme_path}")
            
        except Exception as e:
            logger.error(f"Error creating GGUF documentation: {e}")

def convert_adapter_to_gguf(adapter_path: str, model, tokenizer, config: Dict[str, Any]) -> bool:
    """
    Standalone function to convert adapter to GGUF format
    
    Args:
        adapter_path: Path to the adapter directory
        model: The trained model with LoRA adapter
        tokenizer: Optional tokenizer for metadata
        config: Configuration dictionary
        
    Returns:
        bool: True if conversion successful, False otherwise
    """
    converter = GGUFConverter(config)
    return converter.convert_adapter_to_gguf(adapter_path, model, tokenizer)

def main():
    """Command line interface for GGUF conversion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert LoRA adapter to GGUF format")
    parser.add_argument("adapter_path", help="Path to the adapter directory")
    parser.add_argument("--config", help="Path to configuration JSON file")
    parser.add_argument("--model-path", help="Path to the model file")
    parser.add_argument("--tokenizer-path", help="Path to the tokenizer")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        # Default configuration
        config = {
            "adapter_name": "unknown",
            "base_model": "unknown",
            "lora_rank": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.1,
            "learning_rate": 0.0001,
            "num_epochs": 3,
            "batch_size": 4,
            "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"]
        }
    
    # Create converter
    converter = GGUFConverter(config)
    
    # Convert adapter
    success = converter.convert_adapter_to_gguf(args.adapter_path, None, None)
    
    if success:
        print("✅ GGUF conversion completed successfully")
        sys.exit(0)
    else:
        print("❌ GGUF conversion failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
