# 🚀 Windows Fine-tuning Setup Guide

## ✅ **Complete Windows Setup**

You can now run the entire fine-tuning system on Windows! Here's how:

### **Prerequisites**
1. **Python 3.8+** installed on Windows
2. **Ollama running in Docker** (Windows)
3. **OpenWebUI backend** running (WSL or Windows)

---

## 🎯 **Step-by-Step Startup**

### **Step 1: Start Ollama (Docker)**
```powershell
# Start Ollama in Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull a base model for fine-tuning
docker exec ollama ollama pull qwen2.5:7b
```

### **Step 2: Start OpenWebUI Backend**
**Option A: In WSL (Recommended)**
```bash
# In WSL terminal
cd /mnt/c/Git\ clone/southern-travel-tips-system/backend
./start.sh
```

**Option B: On Windows (Alternative)**
```powershell
# In Windows PowerShell
cd backend
python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

### **Step 3: Start Fine-tuning Backend (Windows)**
```powershell
# Option 1: PowerShell script (Recommended)
.\start_finetuning_windows.ps1

# Option 2: Batch file
.\start_finetuning_windows.bat
```

### **Step 4: Access the Interface**
- **Main App**: http://localhost:8080
- **Fine-tuning Page**: http://localhost:8080/fine-tuning
- **Fine-tuning API**: http://localhost:8001/docs

---

## 🔧 **What Each Component Does**

### **Ollama (Docker - Windows)**
- Runs AI models
- Provides base models for fine-tuning
- Accessible on `localhost:11434`

### **OpenWebUI Backend (WSL/Windows)**
- Main application server
- Serves the web interface
- Accessible on `localhost:8080`

### **Fine-tuning API (Windows)**
- Handles LoRA training requests
- Manages training sessions
- Connects to Ollama Docker
- Accessible on `localhost:8001`

---

## 🎯 **Testing the Setup**

### **1. Check Ollama**
```powershell
curl http://localhost:11434/api/version
```

### **2. Check OpenWebUI**
```powershell
curl http://localhost:8080/api/config
```

### **3. Check Fine-tuning API**
```powershell
curl http://localhost:8001/health
```

### **4. Test Fine-tuning**
1. Go to http://localhost:8080/fine-tuning
2. Select a model (e.g., `qwen2.5:7b`)
3. Upload a dataset (JSONL format)
4. Click "Start Training"

---

## 📋 **Sample Dataset Format**

Create a file called `sample_dataset.jsonl`:
```json
{"prompt": "What is the capital of France?", "response": "The capital of France is Paris."}
{"prompt": "How do you say hello in Spanish?", "response": "Hello in Spanish is 'Hola'."}
{"prompt": "What is 2+2?", "response": "2+2 equals 4."}
```

---

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **"Port already in use"**
   ```powershell
   # Check what's using the port
   netstat -ano | findstr :8001
   # Kill the process (replace PID with actual process ID)
   taskkill /PID <PID> /F
   ```

2. **"Ollama not found"**
   ```powershell
   # Make sure Docker is running
   docker ps
   # Restart Ollama if needed
   docker restart ollama
   ```

3. **"Python not found"**
   - Install Python 3.8+ from https://python.org
   - Make sure it's added to PATH

4. **"Dependencies failed to install"**
   ```powershell
   # Try upgrading pip first
   python -m pip install --upgrade pip
   # Then install requirements
   pip install -r backend/requirements.txt
   ```

---

## 🎉 **Success!**

Once everything is running, you'll have:
- ✅ **Real LoRA fine-tuning** on Windows
- ✅ **Visual training monitoring**
- ✅ **Automatic model export to Ollama**
- ✅ **Full web interface**

The fine-tuning will work entirely on Windows without needing WSL for the training process!
