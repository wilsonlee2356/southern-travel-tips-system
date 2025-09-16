# LoRA Fine-tuning Frontend Startup Script for PowerShell
# This script starts the SvelteKit frontend in Windows

Write-Host "🌐 LoRA Fine-tuning Frontend Startup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Check if Node.js is available
Write-Host "🔍 Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Node.js is available: $nodeVersion" -ForegroundColor Green
    } else {
        throw "Node.js not found"
    }
} catch {
    Write-Host "❌ Node.js is not installed. Please install Node.js 18+" -ForegroundColor Red
    Write-Host "   Visit: https://nodejs.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if npm is available
Write-Host "📦 Checking npm..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ npm is available: v$npmVersion" -ForegroundColor Green
    } else {
        throw "npm not found"
    }
} catch {
    Write-Host "❌ npm is not installed. Please install npm" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies if node_modules doesn't exist
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host "🚀 Starting SvelteKit development server..." -ForegroundColor Green
Write-Host "📡 Frontend will be available at: http://localhost:5173" -ForegroundColor Cyan
Write-Host "🔗 Fine-tuning page: http://localhost:5173/fine-tuning" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  Make sure the backend is running in WSL before using the fine-tuning page" -ForegroundColor Yellow
Write-Host ""

# Start the frontend
npm run dev
