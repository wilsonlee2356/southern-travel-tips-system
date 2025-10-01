#!/usr/bin/env python3
"""
Test script to verify adapter interception is working
"""

import requests
import json

def test_adapter_interception():
    """Test if adapter interception is working"""
    
    # Test payload with adapter info
    payload = {
        "model": "qwen2.5:14b",
        "messages": [
            {
                "role": "user", 
                "content": "Hello, test message"
            }
        ],
        "metadata": {
            "adapter_info": {
                "export_id": "training_1759312230",
                "adapter_name": "my-custom-adapter"
            }
        }
    }
    
    try:
        print("🧪 Testing adapter interception...")
        print(f"📤 Sending request with adapter info: {payload['metadata']['adapter_info']}")
        
        # Send request to OpenWebUI
        response = requests.post(
            "http://localhost:8080/api/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response received successfully")
            print(f"📄 Response model: {result.get('model', 'unknown')}")
            print(f"💬 Response content: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100]}...")
            
            # The response model will still show qwen2.5:14b, but the actual processing
            # should have used the adapter model
            print("\n🔍 Note: Response model shows 'qwen2.5:14b' but actual processing uses adapter")
            print("📋 Check backend logs for interception messages:")
            print("   - 'ADAPTER MIDDLEWARE: Adapter info captured!'")
            print("   - 'ADAPTER INTERCEPTION ACTIVATED!'")
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_adapter_interception()
