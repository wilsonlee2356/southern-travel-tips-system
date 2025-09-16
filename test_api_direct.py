#!/usr/bin/env python3
"""
Direct test of the API endpoint to debug the 422 error
"""

import requests
import json

def test_api_endpoint():
    """Test the exact API endpoint"""
    
    # Create a simple test dataset
    test_data = [
        {"prompt": "Hello", "response": "Hi there!"},
        {"prompt": "How are you?", "response": "I'm doing well, thank you!"}
    ]
    
    # Write to file
    with open("test_dataset.jsonl", "w") as f:
        for item in test_data:
            f.write(json.dumps(item) + "\n")
    
    # Test the API
    url = "http://localhost:8001/api/fine-tuning/start"
    
    # Method 1: Form data with file upload
    print("🧪 Testing with FormData approach...")
    try:
        with open("test_dataset.jsonl", "rb") as f:
            files = {"file": ("test_dataset.jsonl", f, "application/json")}
            data = {
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
            
            response = requests.post(url, files=files, data=data)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Method 2: Check what the API expects
    print("\n🔍 Checking API documentation...")
    try:
        docs_response = requests.get("http://localhost:8001/docs")
        print(f"Docs available: {docs_response.status_code == 200}")
    except Exception as e:
        print(f"Docs error: {e}")

if __name__ == "__main__":
    test_api_endpoint()
