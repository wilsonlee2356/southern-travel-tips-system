#!/usr/bin/env python3
"""
Setup verification script for LoRA Fine-tuning system
Checks if all components are properly configured and accessible
"""

import requests
import subprocess
import sys
import time
import json

def check_ollama_docker():
    """Check if Ollama is running in Docker"""
    print("🔍 Checking Ollama Docker container...")
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=ollama", "--format", "{{.Status}}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ Ollama Docker container is running: {result.stdout.strip()}")
            
            # Test Ollama API
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    print(f"✅ Ollama API is accessible with {len(models)} models")
                    
                    # List available models
                    if models:
                        print("📋 Available models:")
                        for model in models[:5]:  # Show first 5 models
                            name = model.get("name", "Unknown")
                            size = model.get("size", 0)
                            size_gb = size / (1024**3) if size else 0
                            print(f"   - {name} ({size_gb:.1f}GB)")
                        if len(models) > 5:
                            print(f"   ... and {len(models) - 5} more models")
                    else:
                        print("⚠️  No models found. Consider pulling a base model:")
                        print("   docker exec ollama ollama pull qwen2.5:32b")
                    
                    return True
                else:
                    print(f"❌ Ollama API returned status {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"❌ Cannot connect to Ollama API: {e}")
                return False
        else:
            print("❌ Ollama Docker container is not running")
            print("   Start it with: docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama")
            return False
            
    except FileNotFoundError:
        print("❌ Docker command not found. Please install Docker Desktop")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def check_backend_api():
    """Check if backend API is running"""
    print("\n🔍 Checking Backend API...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend API is accessible: {data.get('status', 'Unknown')}")
            
            # Test models endpoint
            try:
                models_response = requests.get("http://localhost:8001/api/models", timeout=5)
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    models = models_data.get("models", [])
                    print(f"✅ Backend can access {len(models)} Ollama models")
                    return True
                else:
                    print(f"⚠️  Backend models endpoint returned status {models_response.status_code}")
                    return True  # Backend is running, just models endpoint issue
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Backend models endpoint error: {e}")
                return True  # Backend is running, just models endpoint issue
        else:
            print(f"❌ Backend API returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Backend API: {e}")
        print("   Make sure the backend is running in WSL with: ./start_backend_wsl.sh")
        return False

def check_frontend():
    """Check if frontend is accessible"""
    print("\n🔍 Checking Frontend...")
    try:
        response = requests.get("http://localhost:5173", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is accessible")
            return True
        else:
            print(f"❌ Frontend returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Frontend: {e}")
        print("   Start it with: start_frontend_windows.bat")
        return False

def check_network_connectivity():
    """Check network connectivity between components"""
    print("\n🔍 Checking Network Connectivity...")
    
    # Check if ports are open
    ports = {
        "Ollama": 11434,
        "Backend": 8001,
        "Frontend": 5173
    }
    
    all_good = True
    for service, port in ports.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"✅ Port {port} ({service}) is open")
            else:
                print(f"❌ Port {port} ({service}) is not accessible")
                all_good = False
        except Exception as e:
            print(f"❌ Error checking port {port} ({service}): {e}")
            all_good = False
    
    return all_good

def main():
    """Main verification function"""
    print("🔧 LoRA Fine-tuning System Verification")
    print("=" * 50)
    
    checks = [
        ("Ollama Docker", check_ollama_docker),
        ("Network Connectivity", check_network_connectivity),
        ("Backend API", check_backend_api),
        ("Frontend", check_frontend)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Verification Summary:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All checks passed! Your system is ready for fine-tuning.")
        print("\n🌐 Access your fine-tuning interface at:")
        print("   http://localhost:5173/fine-tuning")
    else:
        print("⚠️  Some checks failed. Please review the issues above.")
        print("\n📋 Quick Start Guide:")
        print("   1. Start Ollama: docker start ollama")
        print("   2. Start Backend (WSL): ./start_backend_wsl.sh")
        print("   3. Start Frontend (Windows): start_frontend_windows.bat")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
