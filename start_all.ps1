# Complete LoRA Fine-tuning System Startup Script for PowerShell
# This script provides instructions to start all components

Write-Host "🔧 LoRA Fine-tuning System Startup Guide" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 To start the system, run these commands in separate terminals:" -ForegroundColor Yellow
Write-Host ""

Write-Host "1️⃣  Start Ollama (Docker):" -ForegroundColor Green
Write-Host "   docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama" -ForegroundColor White
Write-Host "   docker exec ollama ollama pull qwen2.5:32b" -ForegroundColor White
Write-Host ""

Write-Host "2️⃣  Start Backend (WSL Terminal):" -ForegroundColor Green
Write-Host "   cd /mnt/c/Git\ clone/southern-travel-tips-system" -ForegroundColor White
Write-Host "   chmod +x start_backend_wsl.sh" -ForegroundColor White
Write-Host "   ./start_backend_wsl.sh" -ForegroundColor White
Write-Host ""

Write-Host "3️⃣  Start Frontend (PowerShell):" -ForegroundColor Green
Write-Host "   .\start_frontend_windows.ps1" -ForegroundColor White
Write-Host ""

Write-Host "🌐 Access Points:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5173/fine-tuning" -ForegroundColor White
Write-Host "   Backend API: http://localhost:8001" -ForegroundColor White
Write-Host "   Ollama API: http://localhost:11434" -ForegroundColor White
Write-Host ""

Write-Host "🔍 Verify Setup:" -ForegroundColor Yellow
Write-Host "   python verify_setup.py" -ForegroundColor White
Write-Host ""

Write-Host "Would you like to start the frontend now? (y/n):" -ForegroundColor Yellow
$response = Read-Host

if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "🚀 Starting frontend..." -ForegroundColor Green
    .\start_frontend_windows.ps1
} else {
    Write-Host "👋 Use the commands above to start the system when ready!" -ForegroundColor Cyan
}
