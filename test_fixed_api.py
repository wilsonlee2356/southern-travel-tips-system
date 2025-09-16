#!/usr/bin/env python3
"""
Test the fixed API endpoint
"""

import requests
import json

def test_fixed_api():
    """Test the API with query parameters"""
    
    # Create test dataset
    test_data = [
        {"prompt": "Hello", "response": "Hi there!"},
        {"prompt": "How are you?", "response": "I'm doing well!"}
    ]
    
    with open("test_dataset.jsonl", "w") as f:
        for item in test_data:
            f.write(json.dumps(item) + "\n")
    
    # Test with query parameters
    url = "http://localhost:8001/api/fine-tuning/start"
    params = {
        "base_model": "llama3.2:3b",
        "adapter_name": "test_adapter",
        "learning_rate": "0.0005",
        "num_epochs": "1",
        "batch_size": "1",
        "gradient_accumulation_steps": "4",
        "lora_rank": "16",
        "lora_alpha": "32",
        "lora_dropout": "0.1",
        "target_modules": '["q_proj", "v_proj", "k_proj", "o_proj"]'
    }
    
    try:
        with open("test_dataset.jsonl", "rb") as f:
            files = {"file": ("test_dataset.jsonl", f, "application/json")}
            
            response = requests.post(url, files=files, params=params)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success! Session ID: {result.get('session_id')}")
            else:
                print(f"❌ Error: {response.text}")
                
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_fixed_api()
