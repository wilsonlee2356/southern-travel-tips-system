# my-custom-adapter - GGUF Adapter

## Overview
This is a LoRA adapter converted to GGUF format for use with compatible inference engines.

## File Information
- **File**: adapter.gguf
- **Format**: GGUF (GGML Universal Format)
- **Base Model**: qwen2.5:14b
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
- **LoRA Rank**: 16
- **LoRA Alpha**: 32
- **LoRA Dropout**: 0.1
- **Learning Rate**: 0.0001
- **Epochs**: 3
- **Batch Size**: 4
- **Target Modules**: ['q_proj', 'v_proj', 'k_proj', 'o_proj']

## Output Format
The adapter generates JSON output with the following structure:
```json
{
  "Destination": "東京",
  "Header": "精選東京遊！HK$2,390即刻出發！",
  "Short Comment": "來一趟經濟實惠的東京之旅，賞櫻、品嚐美食，與日本文化近距離接觸。",
  "Summary": "利用ANA全日空航空，從香港前往東京羽田機場，只需HK$2,390便能體驗精采的旅程。"
}
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
