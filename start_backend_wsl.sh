#!/bin/bash

# LoRA Fine-tuning Backend Startup Script for WSL (Windows Ubuntu)
# This script starts the backend API in WSL environment

echo "🔧 LoRA Fine-tuning Backend Startup (WSL)"
echo "=========================================="

# Check if Ollama is accessible from WSL
echo "🔍 Checking Ollama connection..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is accessible from WSL at localhost:11434"
    echo "   Ollama Docker container is running properly"
else
    echo "⚠️  Ollama not accessible at localhost:11434"
    echo "   This is normal if Ollama is running in Docker on Windows"
    echo "   The backend will attempt to connect during startup"
    echo ""
    echo "   To start Ollama Docker container:"
    echo "   docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama"
    echo ""
    echo "   To check if Docker container is running:"
    echo "   docker ps | grep ollama"
fi

# Check if Python is available
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 is available"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    echo "✅ Python is available"
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed. Please install Python 3.8+"
    echo "   sudo apt update && sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Check if pip is available
echo "📦 Checking pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 is available"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    echo "✅ pip is available"
    PIP_CMD="pip"
else
    echo "❌ pip is not installed. Installing pip..."
    sudo apt update && sudo apt install python3-pip
    PIP_CMD="pip3"
fi

# Navigate to backend directory
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
$PIP_CMD install -r requirements.txt

echo "🚀 Starting API server..."
echo "📡 Backend API will be available at: http://localhost:8001"
echo "📚 API documentation at: http://localhost:8001/docs"
echo "🌐 Frontend can connect from Windows at: http://$(hostname -I | awk '{print $1}'):8001"
echo ""

# Start the backend
echo "Starting backend server..."
$PYTHON_CMD start_backend.py
