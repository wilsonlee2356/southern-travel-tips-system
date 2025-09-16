#!/usr/bin/env python3
"""
Test to verify session ID is returned properly
"""

import requests
import json

def test_session_id_return():
    """Test that the API returns a session ID"""
    
    # Create test dataset
    test_data = [
        {"prompt": "Hello", "response": "Hi there!"},
        {"prompt": "How are you?", "response": "I'm doing well!"}
    ]
    
    with open("test_session_dataset.jsonl", "w") as f:
        for item in test_data:
            f.write(json.dumps(item) + "\n")
    
    # Test the API
    url = "http://localhost:8001/api/fine-tuning/start"
    params = {
        "base_model": "llama3.2:3b",
        "adapter_name": "session_test_adapter",
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
        with open("test_session_dataset.jsonl", "rb") as f:
            files = {"file": ("test_session_dataset.jsonl", f, "application/json")}
            
            response = requests.post(url, files=files, params=params)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                session_id = result.get('session_id')
                print(f"✅ Session ID returned: {session_id}")
                
                # Test status endpoint
                status_response = requests.get(f"http://localhost:8001/api/fine-tuning/status/{session_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"✅ Status endpoint working: {status.get('status')}")
                else:
                    print(f"❌ Status endpoint failed: {status_response.status_code}")
                    
            else:
                print(f"❌ Error: {response.text}")
                
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_session_id_return()
