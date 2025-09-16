#!/usr/bin/env python3
"""
Check Ollama Docker Setup
This script helps verify that Ollama is properly running in Docker
"""

import subprocess
import requests
import json
import sys

def check_docker_container():
    """Check if Ollama Docker container is running"""
    print("🔍 Checking Ollama Docker container...")
    
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=ollama", "--format", "{{.Names}}:{{.Status}}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ Ollama container found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama container not running")
            
            # Check if container exists but is stopped
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=ollama", "--format", "{{.Names}}:{{.Status}}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"⚠️  Container exists but stopped: {result.stdout.strip()}")
                print("   Start it with: docker start ollama")
            else:
                print("❌ No Ollama container found")
                print("   Create it with: docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama")
            
            return False
            
    except FileNotFoundError:
        print("❌ Docker command not found. Please install Docker Desktop")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False

def check_ollama_api():
    """Check if Ollama API is accessible"""
    print("\n🔍 Checking Ollama API...")
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ Ollama API is accessible with {len(models)} models")
            
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
                print("⚠️  No models found. Pull a base model:")
                print("   docker exec ollama ollama pull qwen2.5:32b")
            
            return True
        else:
            print(f"❌ Ollama API returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Ollama API at localhost:11434")
        print("   Make sure the Docker container is running and port 11434 is exposed")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama API: {e}")
        return False

def check_wsl_connectivity():
    """Check if WSL can access Ollama"""
    print("\n🔍 Checking WSL connectivity...")
    
    try:
        # Try to check from WSL perspective
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ WSL can access Ollama API")
            return True
        else:
            print(f"❌ WSL cannot access Ollama API (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ WSL connectivity issue: {e}")
        return False

def main():
    """Main check function"""
    print("🔧 Ollama Docker Setup Checker")
    print("=" * 40)
    
    checks = [
        ("Docker Container", check_docker_container),
        ("Ollama API", check_ollama_api),
        ("WSL Connectivity", check_wsl_connectivity)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Check Summary:")
    print("=" * 40)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All checks passed! Ollama Docker setup is working correctly.")
        print("\nYou can now start the backend in WSL:")
        print("   ./start_backend_wsl.sh")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("1. Start Docker Desktop")
        print("2. Run: docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama")
        print("3. Pull a model: docker exec ollama ollama pull qwen2.5:32b")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
