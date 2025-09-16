#!/usr/bin/env python3
"""
Open WebUI Backend Startup Script
This script starts the Open WebUI backend server
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def start_openwebui_backend():
    """Start the Open WebUI backend"""
    try:
        # Change to backend directory
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        os.chdir(backend_dir)
        
        logger.info("🔧 Starting Open WebUI Backend")
        logger.info("=" * 40)
        
        # Set environment variables
        env = os.environ.copy()
        env['CORS_ALLOW_ORIGIN'] = "http://localhost:5173"
        env['PORT'] = "8080"
        
        # Check if virtual environment exists
        venv_path = os.path.join(backend_dir, 'venv')
        if os.path.exists(venv_path):
            logger.info("📦 Using existing virtual environment")
            
            # Activate virtual environment and start server
            if os.name == 'nt':  # Windows
                python_cmd = os.path.join(venv_path, 'Scripts', 'python.exe')
                uvicorn_cmd = os.path.join(venv_path, 'Scripts', 'uvicorn.exe')
            else:  # Linux/Mac
                python_cmd = os.path.join(venv_path, 'bin', 'python')
                uvicorn_cmd = os.path.join(venv_path, 'bin', 'uvicorn')
        else:
            logger.info("📦 Using system Python")
            python_cmd = sys.executable
            uvicorn_cmd = f"{python_cmd} -m uvicorn"
        
        # Start the server
        logger.info("🚀 Starting Open WebUI backend server...")
        logger.info("📡 Backend will be available at: http://localhost:8080")
        logger.info("🌐 Frontend can connect at: http://localhost:5173")
        logger.info("")
        
        # Use the start.sh script if available
        start_script = os.path.join(backend_dir, 'start.sh')
        if os.path.exists(start_script) and os.name != 'nt':
            logger.info("Using start.sh script...")
            result = subprocess.run(['bash', start_script], env=env)
        else:
            # Direct uvicorn command
            cmd = [
                python_cmd, '-m', 'uvicorn', 
                'open_webui.main:app',
                '--port', '8080',
                '--host', '0.0.0.0',
                '--forwarded-allow-ips', '*',
                '--reload'
            ]
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, env=env)
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"Error starting Open WebUI backend: {e}")
        return False

def main():
    """Main function"""
    success = start_openwebui_backend()
    
    if not success:
        logger.error("Failed to start Open WebUI backend")
        sys.exit(1)
    
    logger.info("Open WebUI backend started successfully!")

if __name__ == "__main__":
    main()
