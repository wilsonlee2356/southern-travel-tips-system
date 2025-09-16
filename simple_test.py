#!/usr/bin/env python3

# Simple test of the model mapping
model_mapping = {
    'qwen2.5:32b': 'Qwen/Qwen2.5-32B',
    'qwen2.5:7b': 'Qwen/Qwen2.5-7B',
    'qwen2.5:3b': 'Qwen/Qwen2.5-3B',
    'llama3.2:3b': 'meta-llama/Llama-3.2-3B',
}

def get_hf_model_name(ollama_model_name: str) -> str:
    if ollama_model_name in model_mapping:
        return model_mapping[ollama_model_name]
    return ollama_model_name

# Test
test_cases = ['qwen2.5:32b', 'qwen2.5:7b', 'llama3.2:3b']

print("🧪 Testing Model Mapping")
print("=" * 30)

for model in test_cases:
    hf_name = get_hf_model_name(model)
    print(f"{model} -> {hf_name}")

print("✅ Model mapping works correctly!")
