#!/bin/bash

# LoRA Fine-tuning System Startup Script
# This script starts both the backend API and provides instructions for the frontend

echo "🔧 LoRA Fine-tuning System Startup"
echo "=================================="

# Check if Ollama is running
echo "🔍 Checking Ollama..."
if command -v ollama &> /dev/null; then
    if ollama list &> /dev/null; then
        echo "✅ Ollama is running"
    else
        echo "❌ Ollama is not running. Starting Ollama..."
        ollama serve &
        sleep 3
    fi
else
    echo "❌ Ollama is not installed. Please install Ollama first:"
    echo "   Visit: https://ollama.ai/download"
    exit 1
fi

# Check if Python is available
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python 3 is available"
elif command -v python &> /dev/null; then
    echo "✅ Python is available"
else
    echo "❌ Python is not installed. Please install Python 3.8+"
    exit 1
fi

# Start the backend
echo "🚀 Starting Fine-tuning Backend..."
cd backend

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting API server..."
echo "📡 Backend API will be available at: http://localhost:8001"
echo "📚 API documentation at: http://localhost:8001/docs"
echo ""

# Start the backend in the background
python start_backend.py &
BACKEND_PID=$!

# Wait a moment for the backend to start
sleep 5

echo "✅ Backend started successfully!"
echo ""
echo "🌐 Frontend Instructions:"
echo "=========================="
echo "1. Start your SvelteKit frontend:"
echo "   npm run dev"
echo ""
echo "2. Navigate to: http://localhost:5173/fine-tuning"
echo ""
echo "3. Upload a dataset (JSON or JSONL format)"
echo "4. Configure your training parameters"
echo "5. Start fine-tuning!"
echo ""
echo "📋 Sample dataset available at: backend/sample_dataset.jsonl"
echo ""
echo "🛑 To stop the system, press Ctrl+C"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    echo "✅ Backend stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Keep the script running
wait $BACKEND_PID
