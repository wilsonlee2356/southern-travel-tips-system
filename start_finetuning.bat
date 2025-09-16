@echo off
REM LoRA Fine-tuning System Startup Script for Windows
REM This script starts both the backend API and provides instructions for the frontend

echo 🔧 LoRA Fine-tuning System Startup
echo ==================================

REM Check if Ollama is running
echo 🔍 Checking Ollama...
ollama list >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Ollama is running
) else (
    echo ❌ Ollama is not running. Please start Ollama first:
    echo    ollama serve
    pause
    exit /b 1
)

REM Check if Python is available
echo 🐍 Checking Python...
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Python is available
) else (
    echo ❌ Python is not installed. Please install Python 3.8+
    pause
    exit /b 1
)

REM Start the backend
echo 🚀 Starting Fine-tuning Backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

echo 📦 Activating virtual environment...
call venv\Scripts\activate.bat

echo 📦 Installing dependencies...
pip install -r requirements.txt

echo 🚀 Starting API server...
echo 📡 Backend API will be available at: http://localhost:8001
echo 📚 API documentation at: http://localhost:8001/docs
echo.

REM Start the backend
echo Starting backend server...
python start_backend.py

@REM echo ✅ Backend started successfully!
@REM echo.
@REM echo 🌐 Frontend Instructions:
@REM echo ==========================
@REM echo 1. Start your SvelteKit frontend:
@REM echo    npm run dev
@REM echo.
@REM echo 2. Navigate to: http://localhost:5173/fine-tuning
@REM echo.
@REM echo 3. Upload a dataset (JSON or JSONL format)
@REM echo 4. Configure your training parameters
@REM echo 5. Start fine-tuning!
@REM echo.
@REM echo 📋 Sample dataset available at: backend/sample_dataset.jsonl
@REM echo.
@REM echo 🛑 To stop the system, close this window or press Ctrl+C
@REM pause
