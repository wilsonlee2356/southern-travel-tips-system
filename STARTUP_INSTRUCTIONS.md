# Open WebUI + LoRA Fine-tuning Startup Instructions

## The Issue
You're getting "Open WebUI Backend Required" because Open WebUI needs its Python backend running first, not just the frontend.

## Correct Startup Sequence

### 1. Start Open WebUI Backend (WSL)
```bash
# In WSL terminal
cd /mnt/c/Git\ clone/southern-travel-tips-system
python start_openwebui_backend.py
```

**OR** use the original Open WebUI startup:
```bash
cd backend
bash start.sh
```

### 2. Start Ollama (Docker)
```powershell
# In Windows PowerShell
docker start ollama
# OR if not created:
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

### 3. Start LoRA Fine-tuning Backend (WSL - Separate Terminal)
```bash
# In a NEW WSL terminal
cd /mnt/c/Git\ clone/southern-travel-tips-system
./start_backend_wsl.sh
```

### 4. Access the System
- **Open WebUI**: `http://localhost:8080` (main interface)
- **Fine-tuning Page**: `http://localhost:8080/fine-tuning` (your custom page)
- **LoRA Backend API**: `http://localhost:8001` (fine-tuning API)

## Why This Happens

Open WebUI is a full-stack application that requires:
1. **Python Backend** (FastAPI) - serves the main application
2. **Frontend** (SvelteKit) - the UI you see
3. **Ollama** - the AI model server
4. **LoRA Backend** (optional) - your custom fine-tuning API

## Alternative: Use Open WebUI's Built-in Development Mode

If you want to run everything together:

```bash
# In WSL
cd backend
bash dev.sh
```

This will start Open WebUI with CORS enabled for the frontend development server.

## Port Configuration

- **Open WebUI Backend**: Port 8080 (main application)
- **Frontend Dev Server**: Port 5173 (development only)
- **LoRA Fine-tuning API**: Port 8001 (your custom API)
- **Ollama**: Port 11434 (AI models)

## Quick Fix

If you just want to test the fine-tuning page:

1. **Start Open WebUI Backend**:
   ```bash
   cd backend
   bash start.sh
   ```

2. **Access**: `http://localhost:8080/fine-tuning`

The fine-tuning page should now work within the Open WebUI interface!
