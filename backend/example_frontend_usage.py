#!/usr/bin/env python3
"""
Example: How the frontend can use merged models for inference
This demonstrates the complete workflow from adapter merging to inference
"""

import requests
import json
import time

# Configuration
API_BASE_URL = "http://localhost:8001"

def example_workflow():
    """Complete example workflow for using merged models"""
    
    print("🚀 Adapter Merging and Inference Workflow Example")
    print("=" * 60)
    
    # Step 1: List available adapters
    print("\n1️⃣ Listing available adapters...")
    response = requests.get(f"{API_BASE_URL}/api/adapters/list")
    if response.status_code == 200:
        data = response.json()
        adapters = data.get("adapters", [])
        print(f"   Found {len(adapters)} adapters")
        
        if adapters:
            adapter = adapters[0]  # Use first available adapter
            print(f"   Using adapter: {adapter['adapter_name']} (ID: {adapter['export_id']})")
        else:
            print("   No adapters available. Please run fine-tuning first.")
            return
    else:
        print(f"   Error listing adapters: {response.text}")
        return
    
    # Step 2: Merge adapter with base model
    print(f"\n2️⃣ Merging adapter {adapter['export_id']}...")
    merge_request = {
        "adapter_id": adapter["export_id"],
        "base_model": adapter["base_model"]
    }
    
    response = requests.post(f"{API_BASE_URL}/api/adapters/merge", json=merge_request)
    if response.status_code == 200:
        merge_result = response.json()
        if merge_result["success"]:
            merged_model_name = merge_result["merged_model_name"]
            print(f"   ✅ Successfully merged! Model: {merged_model_name}")
        else:
            print(f"   ❌ Merge failed: {merge_result['error']}")
            return
    else:
        print(f"   ❌ Merge request failed: {response.text}")
        return
    
    # Step 3: Register merged model with Ollama
    print(f"\n3️⃣ Registering merged model with Ollama...")
    response = requests.post(f"{API_BASE_URL}/api/merged-models/{merged_model_name}/register-ollama")
    if response.status_code == 200:
        register_result = response.json()
        if register_result["success"]:
            ollama_model_name = register_result["ollama_model_name"]
            print(f"   ✅ Successfully registered with Ollama: {ollama_model_name}")
        else:
            print(f"   ❌ Ollama registration failed: {register_result['error']}")
            return
    else:
        print(f"   ❌ Ollama registration request failed: {response.text}")
        return
    
    # Step 4: Get inference information
    print(f"\n4️⃣ Getting inference information...")
    response = requests.get(f"{API_BASE_URL}/api/merged-models/{merged_model_name}/inference-info")
    if response.status_code == 200:
        inference_info = response.json()
        if inference_info["success"]:
            print(f"   ✅ Model ready for inference!")
            print(f"   📍 Endpoint: {inference_info['endpoint']}")
            print(f"   🤖 Ollama model: {inference_info['ollama_model_name']}")
        else:
            print(f"   ❌ Error getting inference info: {inference_info['error']}")
            return
    else:
        print(f"   ❌ Inference info request failed: {response.text}")
        return
    
    # Step 5: Generate text using the merged model
    print(f"\n5️⃣ Generating text with merged model...")
    
    # Example prompts for Cantonese travel content
    test_prompts = [
        "機票資料: ANA全日空航空，香港到東京羽田，HK$2,390，10月8日下午2:45出發",
        "機票資料: 大韓航空，香港到多倫多，$8,143，10月27日凌晨0:55出發",
        "機票資料: 國泰航空，香港到新加坡，HK$1,200，11月15日上午10:30出發"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n   Test {i}: {prompt}")
        
        generate_request = {
            "model_name": merged_model_name,
            "prompt": prompt
        }
        
        response = requests.post(f"{API_BASE_URL}/api/inference/generate", json=generate_request)
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print(f"   ✅ Generated response:")
                print(f"   {result['response']}")
            else:
                print(f"   ❌ Generation failed: {result['error']}")
        else:
            print(f"   ❌ Generation request failed: {response.text}")
    
    # Step 6: List merged models
    print(f"\n6️⃣ Listing all merged models...")
    response = requests.get(f"{API_BASE_URL}/api/merged-models/list")
    if response.status_code == 200:
        data = response.json()
        merged_models = data.get("merged_models", [])
        print(f"   Found {len(merged_models)} merged models:")
        for model in merged_models:
            status = "🟢 Ready" if model.get("ollama_registered", False) else "🟡 Not registered"
            print(f"   - {model['merged_model_name']}: {model['adapter_name']} + {model['base_model']} {status}")
    
    print(f"\n🎉 Workflow completed successfully!")
    print(f"   Merged model '{merged_model_name}' is ready for frontend use!")

def test_api_endpoints():
    """Test individual API endpoints"""
    print("🧪 Testing API Endpoints")
    print("=" * 40)
    
    endpoints = [
        ("GET", "/api/adapters/list", "List adapters"),
        ("GET", "/api/merged-models/list", "List merged models"),
    ]
    
    for method, endpoint, description in endpoints:
        print(f"\n{description} ({method} {endpoint})")
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{API_BASE_URL}{endpoint}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success: {len(data.get('adapters', data.get('merged_models', [])))} items")
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_api_endpoints()
    else:
        example_workflow()
