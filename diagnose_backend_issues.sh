#!/bin/bash

# Diagnostic script for backend startup issues
echo "🔍 Diagnosing Backend Startup Issues"
echo "===================================="

# Check if we're in WSL
if grep -q Microsoft /proc/version; then
    echo "✅ Running in WSL"
else
    echo "⚠️  Not running in WSL - this script is designed for WSL"
fi

echo ""
echo "🐍 Python Environment Check:"
echo "---------------------------"
if command -v python3 &> /dev/null; then
    echo "✅ python3: $(which python3)"
    python3 --version
else
    echo "❌ python3 not found"
fi

if command -v python &> /dev/null; then
    echo "✅ python: $(which python)"
    python --version
else
    echo "❌ python not found"
fi

echo ""
echo "📦 Pip Check:"
echo "-------------"
if command -v pip3 &> /dev/null; then
    echo "✅ pip3: $(which pip3)"
    pip3 --version
else
    echo "❌ pip3 not found"
fi

if command -v pip &> /dev/null; then
    echo "✅ pip: $(which pip)"
    pip --version
else
    echo "❌ pip not found"
fi

echo ""
echo "📁 Directory Structure:"
echo "----------------------"
echo "Current directory: $(pwd)"
echo "Backend directory exists: $([ -d "backend" ] && echo "✅ Yes" || echo "❌ No")"
echo "Requirements file exists: $([ -f "backend/requirements.txt" ] && echo "✅ Yes" || echo "❌ No")"
echo "Start script exists: $([ -f "backend/start_backend.py" ] && echo "✅ Yes" || echo "❌ No")"

echo ""
echo "🐳 Docker/Ollama Check:"
echo "----------------------"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama accessible at localhost:11434"
    curl -s http://localhost:11434/api/tags | head -c 100
    echo "..."
else
    echo "❌ Ollama not accessible at localhost:11434"
fi

echo ""
echo "🔧 Virtual Environment Check:"
echo "----------------------------"
if [ -d "backend/venv" ]; then
    echo "✅ Virtual environment exists"
    echo "Activating venv and checking packages..."
    cd backend
    source venv/bin/activate
    echo "Installed packages:"
    pip list | head -10
    cd ..
else
    echo "❌ Virtual environment does not exist"
fi

echo ""
echo "🌐 Network Check:"
echo "----------------"
echo "Local IP: $(hostname -I | awk '{print $1}')"
echo "Port 8001 available: $([ -z "$(netstat -tlnp 2>/dev/null | grep :8001)" ] && echo "✅ Yes" || echo "❌ No - already in use")"

echo ""
echo "📋 Common Issues and Solutions:"
echo "==============================="
echo "1. If Python is missing: sudo apt update && sudo apt install python3 python3-pip python3-venv"
echo "2. If pip is missing: sudo apt install python3-pip"
echo "3. If virtual environment issues: rm -rf backend/venv && cd backend && python3 -m venv venv"
echo "4. If Ollama not accessible: Make sure Docker container is running"
echo "5. If port 8001 in use: Kill process using port or change port in start_backend.py"
echo ""
echo "To run the backend manually:"
echo "cd backend"
echo "source venv/bin/activate"
echo "python start_backend.py"
