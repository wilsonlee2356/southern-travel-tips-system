#!/usr/bin/env python3
"""
FastAPI backend for LoRA Fine-tuning
Handles training requests and provides real-time updates
"""

import os
import sys
import json
import asyncio
import tempfile
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="LoRA Fine-tuning API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global training status storage
training_sessions: Dict[str, Dict[str, Any]] = {}

class TrainingConfig(BaseModel):
    base_model: str
    adapter_name: str
    learning_rate: float
    num_epochs: int
    batch_size: int
    gradient_accumulation_steps: int = 4
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: List[str] = ["q_proj", "v_proj", "k_proj", "o_proj"]

class TrainingStatus(BaseModel):
    session_id: str
    status: str  # "initializing", "training", "completed", "failed", "stopped"
    progress: float
    current_epoch: int
    total_epochs: int
    train_loss: float
    validation_loss: float
    learning_rate: float
    message: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]

@app.get("/")
async def root():
    return {"message": "LoRA Fine-tuning API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/api/fine-tuning/validate-config")
async def validate_config(config: TrainingConfig):
    """Validate training configuration"""
    errors = []
    
    if not config.base_model:
        errors.append("Base model is required")
    
    if not config.adapter_name:
        errors.append("Adapter name is required")
    
    if config.learning_rate <= 0 or config.learning_rate > 1:
        errors.append("Learning rate must be between 0 and 1")
    
    if config.num_epochs <= 0 or config.num_epochs > 100:
        errors.append("Number of epochs must be between 1 and 100")
    
    if config.batch_size <= 0 or config.batch_size > 32:
        errors.append("Batch size must be between 1 and 32")
    
    if config.lora_rank <= 0 or config.lora_rank > 128:
        errors.append("LoRA rank must be between 1 and 128")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

@app.post("/api/fine-tuning/validate-dataset")
async def validate_dataset(file: UploadFile = File(...)):
    """Validate uploaded dataset"""
    try:
        # Read file content
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Parse based on file extension
        if file.filename.endswith('.json'):
            data = json.loads(text_content)
            if not isinstance(data, list):
                return {"valid": False, "error": "JSON file must contain an array"}
        elif file.filename.endswith('.jsonl'):
            data = []
            for line in text_content.split('\n'):
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        return {"valid": False, "error": f"Invalid JSON line: {line}"}
        else:
            return {"valid": False, "error": "Unsupported file format. Use .json or .jsonl"}
        
        # Validate structure
        valid_count = 0
        for item in data:
            if isinstance(item, dict) and 'prompt' in item and 'response' in item:
                valid_count += 1
        
        if valid_count == 0:
            return {"valid": False, "error": "No valid training examples found"}
        
        return {
            "valid": True,
            "total_examples": len(data),
            "valid_examples": valid_count,
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Dataset validation error: {e}")
        return {"valid": False, "error": str(e)}

@app.post("/api/fine-tuning/start")
async def start_training(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    base_model: str = Query(...),
    adapter_name: str = Query(...),
    learning_rate: float = Query(5e-4),
    num_epochs: int = Query(3),
    batch_size: int = Query(1),
    gradient_accumulation_steps: int = Query(4),
    lora_rank: int = Query(16),
    lora_alpha: int = Query(32),
    lora_dropout: float = Query(0.1),
    target_modules: str = Query('["q_proj", "v_proj", "k_proj", "o_proj"]')
):
    """Start fine-tuning process"""
    try:
        # Parse target_modules from JSON string
        try:
            target_modules_list = json.loads(target_modules)
        except json.JSONDecodeError:
            target_modules_list = ["q_proj", "v_proj", "k_proj", "o_proj"]
        
        # Create config object from form parameters
        config = TrainingConfig(
            base_model=base_model,
            adapter_name=adapter_name,
            learning_rate=learning_rate,
            num_epochs=num_epochs,
            batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            lora_rank=lora_rank,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=target_modules_list
        )
        
        # Validate config
        config_validation = await validate_config(config)
        if not config_validation["valid"]:
            raise HTTPException(status_code=400, detail=f"Config validation failed: {config_validation['errors']}")
        
        # Generate session ID
        session_id = f"training_{int(time.time())}"
        
        # Validate dataset
        validation_result = await validate_dataset(file)
        if not validation_result["valid"]:
            raise HTTPException(status_code=400, detail=validation_result["error"])
        
        # Initialize training session
        training_sessions[session_id] = {
            "session_id": session_id,
            "status": "initializing",
            "progress": 0.0,
            "current_epoch": 0,
            "total_epochs": config.num_epochs,
            "train_loss": 0.0,
            "validation_loss": 0.0,
            "learning_rate": config.learning_rate,
            "message": "Initializing training...",
            "start_time": datetime.now(),
            "end_time": None,
            "error": None,
            "config": config.dict(),
            "dataset_filename": file.filename
        }
        
        # Save dataset to temporary file
        temp_dataset_path = f"/tmp/dataset_{session_id}.jsonl"
        with open(temp_dataset_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Start training in background
        background_tasks.add_task(run_training_async, session_id, config.dict(), temp_dataset_path)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Training started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fine-tuning/status/{session_id}")
async def get_training_status(session_id: str):
    """Get training status"""
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    return training_sessions[session_id]

@app.post("/api/fine-tuning/stop/{session_id}")
async def stop_training(session_id: str):
    """Stop training process"""
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    session = training_sessions[session_id]
    if session["status"] in ["completed", "failed", "stopped"]:
        raise HTTPException(status_code=400, detail="Training is not running")
    
    session["status"] = "stopped"
    session["message"] = "Training stopped by user"
    session["end_time"] = datetime.now()
    
    return {"success": True, "message": "Training stopped"}

@app.get("/api/fine-tuning/sessions")
async def list_training_sessions():
    """List all training sessions"""
    return {
        "sessions": list(training_sessions.values())
    }

@app.delete("/api/fine-tuning/session/{session_id}")
async def delete_training_session(session_id: str):
    """Delete training session"""
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    del training_sessions[session_id]
    return {"success": True, "message": "Session deleted"}

async def run_training_async(session_id: str, config: Dict[str, Any], dataset_path: str):
    """Run training asynchronously"""
    try:
        # Update status
        training_sessions[session_id]["status"] = "training"
        training_sessions[session_id]["message"] = "Training in progress..."
        
        # Create temporary config file
        config_path = f"/tmp/config_{session_id}.json"
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # Run training script
        script_path = Path(__file__).parent / "fine_tuning_script.py"
        
        cmd = [
            sys.executable,
            str(script_path),
            "--config", config_path,
            "--dataset", dataset_path
        ]
        
        logger.info(f"Running training command: {' '.join(cmd)}")
        
        # Start subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor progress
        while process.poll() is None:
            # Read output for progress updates
            try:
                output = process.stdout.readline()
                if output:
                    # Parse training progress from output
                    if "epoch" in output.lower() and "loss" in output.lower():
                        # Extract progress information
                        update_progress_from_output(session_id, output)
                
                # Check if training was stopped
                if training_sessions[session_id]["status"] == "stopped":
                    process.terminate()
                    training_sessions[session_id]["status"] = "stopped"
                    training_sessions[session_id]["message"] = "Training stopped by user"
                    training_sessions[session_id]["end_time"] = datetime.now()
                    return
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error monitoring training: {e}")
                break
        
        # Wait for completion
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Training completed successfully
            training_sessions[session_id]["status"] = "completed"
            training_sessions[session_id]["progress"] = 100.0
            training_sessions[session_id]["message"] = "Training completed successfully!"
            training_sessions[session_id]["end_time"] = datetime.now()
            
            # Parse final result
            try:
                result = json.loads(stdout)
                if result.get("success"):
                    training_sessions[session_id]["message"] = result.get("message", "Training completed!")
            except:
                pass
                
        else:
            # Training failed
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Training failed"
            training_sessions[session_id]["error"] = stderr
            training_sessions[session_id]["end_time"] = datetime.now()
    
    except Exception as e:
        logger.error(f"Training error: {e}")
        training_sessions[session_id]["status"] = "failed"
        training_sessions[session_id]["message"] = "Training failed"
        training_sessions[session_id]["error"] = str(e)
        training_sessions[session_id]["end_time"] = datetime.now()
    
    finally:
        # Cleanup
        try:
            os.remove(config_path)
            os.remove(dataset_path)
        except:
            pass

def update_progress_from_output(session_id: str, output: str):
    """Update progress from training output"""
    try:
        # Simple progress parsing - in a real implementation, 
        # you'd want more sophisticated parsing
        if "epoch" in output and "/" in output:
            parts = output.split()
            for i, part in enumerate(parts):
                if "epoch" in part and i + 1 < len(parts):
                    epoch_info = parts[i + 1]
                    if "/" in epoch_info:
                        current, total = epoch_info.split("/")
                        training_sessions[session_id]["current_epoch"] = int(current)
                        training_sessions[session_id]["total_epochs"] = int(total)
                        
                        # Calculate progress
                        progress = (int(current) / int(total)) * 100
                        training_sessions[session_id]["progress"] = min(progress, 100.0)
        
        # Parse loss values
        if "loss" in output.lower():
            # Extract loss values from output
            import re
            loss_match = re.search(r'loss[:\s]*([0-9.]+)', output.lower())
            if loss_match:
                training_sessions[session_id]["train_loss"] = float(loss_match.group(1))
    
    except Exception as e:
        logger.warning(f"Error parsing training output: {e}")

@app.get("/api/models")
async def list_models():
    """List available Ollama models"""
    try:
        # Try to get models via Ollama API first (works with Docker)
        import requests
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("models", []):
                    models.append({
                        "name": model.get("name", ""),
                        "size": f"{model.get('size', 0) / (1024**3):.1f}GB",
                        "modified": model.get("modified_at", "").split("T")[0] if model.get("modified_at") else None
                    })
                return {"models": models}
        except Exception as api_error:
            logger.warning(f"Ollama API failed: {api_error}")
        
        # Fallback to ollama command line
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            models = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        models.append({
                            "name": parts[0],
                            "size": parts[1],
                            "modified": parts[2] if len(parts) > 2 else None
                        })
            return {"models": models}
        else:
            return {"models": [], "error": result.stderr}
    
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return {"models": [], "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "fine_tuning_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
