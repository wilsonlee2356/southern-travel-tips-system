# LoRA Fine-tuning Setup Guide

## Multi-Environment Setup

This guide helps you set up LoRA fine-tuning across different environments:
- **Ollama**: Docker on Windows
- **Backend**: WSL (Windows Ubuntu)
- **Frontend**: Windows Terminal

## Prerequisites

### 1. Ollama Docker Setup
```bash
# Start Ollama in Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull a base model (example)
docker exec ollama ollama pull qwen2.5:32b
```

### 2. WSL Setup
```bash
# Update WSL
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Git (if needed)
sudo apt install git -y
```

### 3. Windows Setup
- Install Node.js 18+ from [nodejs.org](https://nodejs.org/)
- Install Git for Windows (if needed)

## Starting the System

### Step 1: Start Ollama (Docker)
```bash
# In Windows PowerShell/CMD
docker start ollama
# OR if not created yet:
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

### Step 2: Start Backend (WSL)
```bash
# In WSL terminal
cd /path/to/your/project
chmod +x start_backend_wsl.sh
./start_backend_wsl.sh
```

### Step 3: Start Frontend (Windows)
```cmd
# In Windows Terminal/CMD
cd C:\path\to\your\project
start_frontend_windows.bat
```

## Configuration

### Network Access
- **Frontend → Backend**: `http://localhost:8001` (WSL exposes port to Windows)
- **Backend → Ollama**: `http://localhost:11434` (Docker port mapping)
- **Frontend → Ollama**: `http://localhost:11434` (Direct access)

### Port Configuration
- **Ollama**: Port 11434 (Docker)
- **Backend API**: Port 8001 (WSL)
- **Frontend**: Port 5173 (Windows)

## Troubleshooting

### Ollama Connection Issues
```bash
# Check if Ollama container is running
docker ps | grep ollama

# Check Ollama logs
docker logs ollama

# Test Ollama API
curl http://localhost:11434/api/tags
```

### Backend Connection Issues
```bash
# In WSL, check if backend is accessible from Windows
curl http://localhost:8001/health

# Check WSL IP address
hostname -I
```

### Frontend Connection Issues
```bash
# In Windows, test backend connection
curl http://localhost:8001/health

# Check if ports are accessible
netstat -an | findstr :8001
netstat -an | findstr :11434
```

## File Paths

### Windows Paths
- Frontend: `C:\Git clone\southern-travel-tips-system`
- Start script: `start_frontend_windows.bat`

### WSL Paths
- Backend: `/mnt/c/Git clone/southern-travel-tips-system/backend`
- Start script: `start_backend_wsl.sh`

## Sample Commands

### Pull Models in Docker
```bash
docker exec ollama ollama pull qwen2.5:32b
docker exec ollama ollama pull llama3.1:8b
docker exec ollama ollama list
```

### Test Backend API
```bash
# In WSL
curl http://localhost:8001/health
curl http://localhost:8001/api/models
```

### Test Frontend
1. Open `http://localhost:5173/fine-tuning` in browser
2. Upload a dataset
3. Configure training parameters
4. Start fine-tuning

## Development Workflow

1. **Start Ollama Docker**: `docker start ollama`
2. **Start Backend (WSL)**: `./start_backend_wsl.sh`
3. **Start Frontend (Windows)**: `start_frontend_windows.bat`
4. **Access Interface**: `http://localhost:5173/fine-tuning`
5. **Monitor Training**: Real-time updates in browser

## Stopping the System

1. **Frontend**: Ctrl+C in Windows terminal
2. **Backend**: Ctrl+C in WSL terminal
3. **Ollama**: `docker stop ollama`

## Notes

- The backend runs in WSL but is accessible from Windows via localhost
- Ollama runs in Docker but is accessible from both WSL and Windows
- All components communicate via localhost with different ports
- Training data and models are stored in WSL filesystem
- Fine-tuned models are automatically registered with Docker Ollama
