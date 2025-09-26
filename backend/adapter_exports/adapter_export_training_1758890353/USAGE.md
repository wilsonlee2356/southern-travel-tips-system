# my-custom-adapter - Adapter Usage Instructions

## Overview
This is a fine-tuned LoRA adapter for generating Cantonese travel content in JSON format.

## Adapter Information
- **Adapter Name**: my-custom-adapter
- **Base Model**: qwen2.5:14b
- **Created**: 2025-09-26 20:41:30
- **Session ID**: training_1758890353

## How to Use This Adapter

### Option 1: With Transformers Library
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load base model
base_model = AutoModelForCausalLM.from_pretrained("qwen2.5-14b")
tokenizer = AutoTokenizer.from_pretrained("qwen2.5-14b")

# Load adapter
model = PeftModel.from_pretrained(base_model, "adapter/")

# Use for inference
def generate_travel_content(flight_data):
    prompt = f"""你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。請根據提供的機票資料，只輸出JSON格式，不要輸出任何其他文字。包含以下欄位：\n- Destination（目的地）：簡潔的中文目的地名稱\n- Header（標題）：吸引人的標題，由三部份組成:機票評論, 航空公司目的地連價格, 出發資訊\n- Short Comment（簡短評論）：1-2句簡短評價，說服他人購買，指出有何吸引之處\n- Summary（詳細總結）：詳細的旅遊推薦內容，包含航班資訊、簡短景點介紹、價錢吸引處、或者行李寬限等\n確保JSON格式完整，以}結尾。\n\n### 機票資料:\n{flight_data}\n\n### 旅遊推薦內容:"""
    
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
base_model = AutoModelForCausalLM.from_pretrained("qwen2.5-14b")
tokenizer = AutoTokenizer.from_pretrained("qwen2.5-14b")

# Load and merge adapter
model = PeftModel.from_pretrained(base_model, "adapter/")
merged_model = model.merge_and_unload()

# Save merged model
merged_model.save_pretrained("merged_model")
tokenizer.save_pretrained("merged_model")
```

### Option 3: Create Ollama Modelfile
```dockerfile
FROM qwen2.5:14b

SYSTEM """你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。你已經經過專門訓練，能夠根據機票資料寫出結構化的旅遊推薦內容。請只輸出JSON格式，不要輸出任何其他文字。包含以下欄位：\n- Destination（目的地）：簡潔的中文目的地名稱，如「東京」、「悉尼」\n- Header（標題）：吸引人的標題，由三部份組成:機票評論, 航空公司目的地連價格, 出發資訊\n- Short Comment（簡短評論）：1-2句簡短評價，說服他人購買，指出有何吸引之處\n- Summary（詳細總結）：詳細的旅遊推薦內容，包含航班資訊、簡短景點介紹、價錢吸引處、或者行李寬限等\n確保JSON格式完整，以}結尾。"""

TEMPLATE """你是一個專門分析機票優惠的助手，根據指定語法，用粵語（繁體字）口語化寫出吸引人的旅遊內容。請根據提供的機票資料，只輸出JSON格式，不要輸出任何其他文字。\n\n### 機票資料:\n{{ .Prompt }}\n\n### 旅遊推薦內容:"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER stop "}"
```

## Training Configuration
- Learning Rate: 0.0001
- Epochs: 3
- Batch Size: 4
- LoRA Rank: 16
- LoRA Alpha: 32
- LoRA Dropout: 0.1
- Target Modules: ['q_proj', 'v_proj', 'k_proj', 'o_proj']

## Output Format
The adapter generates JSON output with the following structure:
```json
{
  "Destination": "東京",
  "Header": "精選東京遊！HK$2,390即刻出發！",
  "Short Comment": "來一趟經濟實惠的東京之旅，賞櫻、品嚐美食，與日本文化近距離接觸。",
  "Summary": "利用ANA全日空航空，從香港前往東京羽田機場，只需HK$2,390便能體驗精采的旅程。10月8日搭乘下午兩點四十五分航班，帶來便利的時間安排。行李規定為一件不超過23kg的行李，讓你輕鬆享受旅程。"
}
```

## Files Included
- `adapter/` - The LoRA adapter files
- `adapter_config.json` - Adapter configuration and metadata
- `USAGE.md` - This usage guide
- `training_training_1758890353.log` - Training log
- `training_info_training_1758890353.json` - Training configuration

## Notes
- This adapter is specifically trained for Cantonese (Traditional Chinese) travel content generation
- The output is always in JSON format with the specified fields
- Use temperature 0.7 for balanced creativity and consistency
- The adapter works best with the base model it was trained on
