#!/usr/bin/env python3
"""
Test script for the LoRA Fine-tuning API
"""

import requests
import json

def test_api_connection():
    """Test basic API connection"""
    try:
        response = requests.get("http://localhost:8001/health")
        if response.status_code == 200:
            print("✅ API is running and healthy")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API at http://localhost:8001")
        print("Make sure the backend is running with: ./start_backend_wsl.sh")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_models_endpoint():
    """Test models endpoint"""
    try:
        response = requests.get("http://localhost:8001/api/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ Models endpoint working. Found {len(models)} models")
            for model in models[:3]:  # Show first 3 models
                print(f"  - {model.get('name', 'Unknown')} ({model.get('size', 'Unknown size')})")
            return True
        else:
            print(f"❌ Models endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing models endpoint: {e}")
        return False

def test_ollama_connection():
    """Test Ollama connection"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            ollama_models = response.json()
            print(f"✅ Ollama is running. Found {len(ollama_models.get('models', []))} models")
            return True
        else:
            print(f"❌ Ollama connection failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama at http://localhost:11434")
        print("Make sure Ollama is running in Docker")
        return False
    except Exception as e:
        print(f"❌ Error testing Ollama: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing LoRA Fine-tuning API")
    print("=" * 40)
    
    # Test API connection
    api_ok = test_api_connection()
    
    if api_ok:
        # Test models endpoint
        test_models_endpoint()
    
    # Test Ollama connection
    test_ollama_connection()
    
    print("\n" + "=" * 40)
    if api_ok:
        print("✅ Backend API is ready for fine-tuning!")
    else:
        print("❌ Backend API needs to be started")
        print("Run: ./start_backend_wsl.sh")

if __name__ == "__main__":
    main()
