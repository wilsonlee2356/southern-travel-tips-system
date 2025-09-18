# PowerShell script to start LoRA Fine-tuning Backend on Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting LoRA Fine-tuning Backend (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Navigate to backend directory
Set-Location "backend"

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "🔧 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv --without-pip
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "🔧 Installing pip in virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
    python -m ensurepip --upgrade
    deactivate
}

# Remove problematic lib64 symlink if it exists
if (Test-Path "venv\lib64") {
    Write-Host "🔧 Fixing Windows symlink issue..." -ForegroundColor Yellow
    Remove-Item "venv\lib64" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "✅ Virtual environment ready" -ForegroundColor Green
Write-Host ""

# Activate virtual environment
& "venv\Scripts\Activate.ps1"

# Install/upgrade dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Check if Ollama is running
Write-Host "🔍 Checking Ollama connection..." -ForegroundColor Yellow
try {
    $ollamaResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/version" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama not detected on localhost:11434" -ForegroundColor Yellow
    Write-Host "Please make sure Ollama is running" -ForegroundColor Yellow
    Write-Host "You can start it with: docker run -d -p 11434:11434 ollama/ollama" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "🚀 Starting fine-tuning API server..." -ForegroundColor Cyan
Write-Host "📡 API will be available at: http://localhost:8001" -ForegroundColor Green
Write-Host "📚 API docs at: http://localhost:8001/docs" -ForegroundColor Green
Write-Host "🌐 Frontend can connect at: http://localhost:8080/fine-tuning" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the API server
python fine_tuning_api.py

Read-Host "Press Enter to exit"