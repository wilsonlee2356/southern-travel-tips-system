#!/usr/bin/env python3
"""
Test script to simulate the training request that's failing
"""

import requests
import json

def create_test_dataset():
    """Create a test dataset file"""
    test_data = [
        {"prompt": "What is the capital of France?", "response": "The capital of France is Paris."},
        {"prompt": "How do you say hello in Spanish?", "response": "Hello in Spanish is 'Hola'."},
        {"prompt": "What is 2+2?", "response": "2+2 equals 4."}
    ]
    
    with open("test_dataset.jsonl", "w") as f:
        for item in test_data:
            f.write(json.dumps(item) + "\n")
    
    return "test_dataset.jsonl"

def test_training_request():
    """Test the training request"""
    # Create test dataset
    dataset_file = create_test_dataset()
    
    # Prepare the request
    files = {
        'file': ('test_dataset.jsonl', open(dataset_file, 'rb'), 'application/json')
    }
    
    data = {
        'base_model': 'llama3.2:3b',
        'adapter_name': 'test_adapter',
        'learning_rate': '0.0005',
        'num_epochs': '1',
        'batch_size': '1',
        'gradient_accumulation_steps': '4',
        'lora_rank': '16',
        'lora_alpha': '32',
        'lora_dropout': '0.1',
        'target_modules': '["q_proj", "v_proj", "k_proj", "o_proj"]'
    }
    
    try:
        print("🧪 Testing training request...")
        print(f"Data: {data}")
        
        response = requests.post(
            "http://localhost:8001/api/fine-tuning/start",
            files=files,
            data=data
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Training started successfully!")
            print(f"Session ID: {result.get('session_id')}")
            return True
        else:
            print(f"❌ Training request failed!")
            try:
                error = response.json()
                print(f"Error: {json.dumps(error, indent=2)}")
            except:
                print(f"Error Text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during request: {e}")
        return False
    finally:
        files['file'][1].close()

def main():
    """Main test function"""
    print("🧪 Testing Training Request")
    print("=" * 40)
    
    success = test_training_request()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Training request is working!")
    else:
        print("❌ Training request needs debugging")

if __name__ == "__main__":
    main()
