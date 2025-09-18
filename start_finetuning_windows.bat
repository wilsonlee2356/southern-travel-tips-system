@echo off
echo ========================================
echo Starting LoRA Fine-tuning Backend (Windows)
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Navigate to backend directory
cd backend

REM Check if virtual environment exists
if not exist "venv" (
    echo 🔧 Creating virtual environment...
    python -m venv venv --without-pip
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo 🔧 Installing pip in virtual environment...
    call venv\Scripts\activate.bat
    python -m ensurepip --upgrade
    deactivate
)

REM Remove problematic lib64 symlink if it exists
if exist "venv\lib64" (
    echo 🔧 Fixing Windows symlink issue...
    rmdir /s /q "venv\lib64" 2>nul
)

echo ✅ Virtual environment ready
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo 📦 Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed
echo.

REM Check if Ollama is running
echo 🔍 Checking Ollama connection...
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Ollama not detected on localhost:11434
    echo Please make sure Ollama is running
    echo You can start it with: docker run -d -p 11434:11434 ollama/ollama
    echo.
)

echo 🚀 Starting fine-tuning API server...
echo 📡 API will be available at: http://localhost:8001
echo 📚 API docs at: http://localhost:8001/docs
echo 🌐 Frontend can connect at: http://localhost:8080/fine-tuning
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the API server
python fine_tuning_api.py

pause
