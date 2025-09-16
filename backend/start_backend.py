#!/usr/bin/env python3
"""
Startup script for the LoRA Fine-tuning backend
"""

import os
import sys
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_ollama():
    """Check if Ollama is running (Docker or local)"""
    try:
        # First try to check via HTTP API (works with Docker)
        import requests
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama is accessible via API (Docker)")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Fallback to ollama command (local installation)
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ Ollama is running (local)")
            return True
        else:
            logger.warning("⚠️ Ollama command not available, but API check will be attempted")
            return True  # Allow startup, API check will handle Docker case
    except Exception as e:
        logger.warning(f"⚠️ Error checking Ollama: {e}")
        logger.info("Will attempt to connect via API during startup")
        return True  # Allow startup, let the API handle the connection

def install_dependencies():
    """Install Python dependencies"""
    try:
        logger.info("📦 Installing Python dependencies...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Dependencies installed successfully")
            return True
        else:
            logger.error(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error installing dependencies: {e}")
        return False

def start_api():
    """Start the FastAPI server"""
    try:
        logger.info("🚀 Starting Fine-tuning API server...")
        logger.info("📡 API will be available at: http://localhost:8001")
        logger.info("📚 API documentation at: http://localhost:8001/docs")
        
        # Start the server
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'fine_tuning_api:app',
            '--host', '0.0.0.0',
            '--port', '8001',
            '--reload'
        ])
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Error starting server: {e}")

def main():
    """Main startup function"""
    logger.info("🔧 LoRA Fine-tuning Backend Startup")
    logger.info("=" * 50)
    
    # Check Ollama
    if not check_ollama():
        logger.error("Please ensure Ollama is running before starting the backend")
        logger.info("You can start Ollama with: ollama serve")
        return
    
    # Install dependencies
    if not install_dependencies():
        logger.error("Failed to install dependencies. Please check the requirements.txt file")
        return
    
    # Start API
    start_api()

if __name__ == "__main__":
    main()
