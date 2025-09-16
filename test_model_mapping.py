#!/usr/bin/env python3
"""
Test the model name mapping
"""

import sys
import os
sys.path.append('backend')

from fine_tuning_script import LoRAFineTuner

def test_model_mapping():
    """Test model name mapping"""
    trainer = LoRAFineTuner({})
    
    test_cases = [
        ('qwen2.5:32b', 'Qwen/Qwen2.5-32B'),
        ('qwen2.5:7b', 'Qwen/Qwen2.5-7B'),
        ('llama3.2:3b', 'meta-llama/Llama-3.2-3B'),
        ('llama3.1:8b', 'meta-llama/Llama-3.1-8B'),
        ('mistral:7b', 'mistralai/Mistral-7B-v0.1')
    ]
    
    print("🧪 Testing Model Name Mapping")
    print("=" * 40)
    
    for ollama_name, expected_hf_name in test_cases:
        actual_hf_name = trainer.get_hf_model_name(ollama_name)
        status = "✅" if actual_hf_name == expected_hf_name else "❌"
        print(f"{status} {ollama_name} -> {actual_hf_name}")
        if actual_hf_name != expected_hf_name:
            print(f"   Expected: {expected_hf_name}")

if __name__ == "__main__":
    test_model_mapping()
