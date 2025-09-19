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

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query, Request
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
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://localhost:8080",  # OpenWebUI default port
        "http://127.0.0.1:5173",  # Alternative localhost format
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle CORS preflight requests"""
    return {"message": "OK"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now(),
        "active_sessions": len(training_sessions),
        "python_executable": sys.executable,
        "script_path": str(Path(__file__).parent / "fine_tuning_script.py")
    }

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

def validate_dataset_content(content: bytes, filename: str):
    """Validate dataset content"""
    try:
        text_content = content.decode('utf-8')
        
        # Parse based on file extension
        if filename.endswith('.json'):
            data = json.loads(text_content)
            if not isinstance(data, list):
                return {"valid": False, "error": "JSON file must contain an array"}
        elif filename.endswith('.jsonl'):
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
            "filename": filename,
            "size": len(content)
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}

@app.post("/api/fine-tuning/validate-dataset")
async def validate_dataset(file: UploadFile = File(...)):
    """Validate uploaded dataset"""
    try:
        # Read file content
        content = await file.read()
        result = await validate_dataset_content(content, file.filename)
        
        # Add debug information
        if not result["valid"]:
            # Show first few lines of the file for debugging
            try:
                text_content = content.decode('utf-8')
                lines = text_content.split('\n')[:5]  # First 5 lines
                result["debug_lines"] = lines
                result["file_size"] = len(content)
                logger.error(f"Dataset validation failed for {file.filename}. First 5 lines: {lines}")
            except:
                pass
        
        return result
        
    except Exception as e:
        logger.error(f"Dataset validation error: {e}")
        return {"valid": False, "error": str(e)}

async def validate_dataset_content(content: bytes, filename: str) -> Dict[str, Any]:
    """Validate dataset content from bytes"""
    try:
        text_content = content.decode('utf-8')
        
        # Parse based on file extension
        if filename.endswith('.json'):
            data = json.loads(text_content)
            if not isinstance(data, list):
                return {"valid": False, "error": "JSON file must contain an array"}
        elif filename.endswith('.jsonl'):
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
            "filename": filename,
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Dataset content validation error: {e}")
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
        
        # Read file content once and store it
        file_content = await file.read()
        
        # Validate dataset using the content
        validation_result = await validate_dataset_content(file_content, file.filename)
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
        
        # Save and convert dataset to proper JSONL format (Windows compatible)
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_dataset_path = os.path.join(temp_dir, f"dataset_{session_id}.jsonl")
        
        # Convert the uploaded file to proper JSONL format
        try:
            # First, decode the content and parse it
            text_content = file_content.decode('utf-8')
            
            if file.filename.endswith('.json'):
                # Handle JSON array format
                data = json.loads(text_content)
                if not isinstance(data, list):
                    raise ValueError("JSON file must contain an array of training examples")
            elif file.filename.endswith('.jsonl'):
                # Handle JSONL format - parse line by line
                data = []
                for line_num, line in enumerate(text_content.split('\n'), 1):
                    if line.strip():
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
                            continue
            else:
                raise ValueError("Unsupported file format. Use .json or .jsonl")
            
            # Convert to proper JSONL format and save
            with open(temp_dataset_path, 'w', encoding='utf-8') as f:
                for item in data:
                    if isinstance(item, dict) and 'prompt' in item and 'response' in item:
                        # Keep the original format that the training script expects
                        training_example = {
                            "prompt": item['prompt'],
                            "response": item['response']
                        }
                        f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
            
            logger.info(f"Successfully converted dataset with {len(data)} examples to JSONL format")
            
        except Exception as e:
            logger.error(f"Error processing dataset: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid dataset format: {str(e)}")
        
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
async def get_training_status(session_id: str, request: Request):
    """Get training status"""
    # Log CORS request for debugging
    origin = request.headers.get("origin")
    if origin:
        logger.info(f"CORS request from origin: {origin}")
    
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    # Filter out internal process references that can't be serialized
    session = training_sessions[session_id]
    clean_session = {k: v for k, v in session.items() if not k.startswith('_')}
    return clean_session

@app.post("/api/fine-tuning/stop/{session_id}")
async def stop_training(session_id: str):
    """Stop training process"""
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    session = training_sessions[session_id]
    if session["status"] in ["completed", "failed", "stopped"]:
        raise HTTPException(status_code=400, detail="Training is not running")
    
    # Mark as stopped (the monitoring loop will handle process termination)
    session["status"] = "stopped"
    session["message"] = "Training stop requested..."
    
    # Try to terminate the process if we have a reference
    if "_process" in session:
        try:
            process = session["_process"]
            if hasattr(process, 'process') and process.process.poll() is None:  # Process is still running
                process.terminate()
                logger.info(f"Terminated training process for session {session_id}")
        except Exception as e:
            logger.warning(f"Error terminating process for session {session_id}: {e}")
    
    return {"success": True, "message": "Training stop requested"}

@app.get("/api/fine-tuning/sessions")
async def list_training_sessions():
    """List all training sessions"""
    # Filter out internal process references that can't be serialized
    serializable_sessions = []
    for session in training_sessions.values():
        # Create a copy without the internal process reference
        clean_session = {k: v for k, v in session.items() if not k.startswith('_')}
        serializable_sessions.append(clean_session)
    
    return {
        "sessions": serializable_sessions
    }

@app.delete("/api/fine-tuning/session/{session_id}")
async def delete_training_session(session_id: str):
    """Delete training session"""
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    del training_sessions[session_id]
    return {"success": True, "message": "Session deleted"}

@app.get("/api/fine-tuning/logs/{session_id}")
async def get_training_logs(session_id: str):
    """Get training logs for a session"""
    if session_id not in training_sessions:
        raise HTTPException(status_code=404, detail="Training session not found")
    
    session = training_sessions[session_id]
    
    # Try to find training log file
    log_file = f"/tmp/dataset_{session_id}/training_output.log"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                log_content = f.read()
            return {
                "success": True,
                "logs": log_content,
                "log_file": log_file
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not read log file: {str(e)}",
                "log_file": log_file
            }
    else:
        return {
            "success": False,
            "error": "Training log file not found",
            "log_file": log_file
        }

async def run_training_async(session_id: str, config: Dict[str, Any], dataset_path: str):
    """Run training asynchronously using proper async subprocess handling"""
    try:
        # Update status
        training_sessions[session_id]["status"] = "training"
        training_sessions[session_id]["message"] = "Training in progress..."
        
        # Create temporary config file (Windows compatible)
        import tempfile
        temp_dir = tempfile.gettempdir()
        config_path = os.path.join(temp_dir, f"config_{session_id}.json")
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
        
        # Log additional debugging info
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Python executable exists: {os.path.exists(sys.executable)}")
        logger.info(f"Script path: {script_path}")
        logger.info(f"Script path exists: {os.path.exists(str(script_path))}")
        logger.info(f"Config path: {config_path}")
        logger.info(f"Config file exists: {os.path.exists(config_path)}")
        logger.info(f"Dataset path: {dataset_path}")
        logger.info(f"Dataset file exists: {os.path.exists(dataset_path)}")
        logger.info(f"Working directory: {Path(__file__).parent}")
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # First, test if we can run the script at all
        try:
            logger.info("Testing script execution with --help...")
            test_result = subprocess.run([
                sys.executable, str(script_path), "--help"
            ], capture_output=True, text=True, timeout=10, cwd=Path(__file__).parent)
            
            if test_result.returncode != 0:
                error_msg = f"Script test failed with return code {test_result.returncode}: {test_result.stderr}"
                logger.error(error_msg)
                training_sessions[session_id]["status"] = "failed"
                training_sessions[session_id]["message"] = "Training script execution test failed"
                training_sessions[session_id]["error"] = error_msg
                training_sessions[session_id]["end_time"] = datetime.now()
                return
            else:
                logger.info("Script test passed successfully")
                
        except subprocess.TimeoutExpired:
            error_msg = "Script test timed out"
            logger.error(error_msg)
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Training script test timed out"
            training_sessions[session_id]["error"] = error_msg
            training_sessions[session_id]["end_time"] = datetime.now()
            return
        except Exception as e:
            error_msg = f"Script test failed: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Training script test failed"
            training_sessions[session_id]["error"] = error_msg
            training_sessions[session_id]["end_time"] = datetime.now()
            return

        # Use subprocess.Popen as asyncio.create_subprocess_exec has issues on Windows
        try:
            logger.info(f"Attempting to create subprocess with command: {cmd}")
            logger.info("Using subprocess.Popen for Windows compatibility")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for real-time output
                text=True,
                bufsize=0,  # Unbuffered for real-time output
                universal_newlines=True,
                cwd=Path(__file__).parent
            )
            logger.info(f"Process started successfully with PID: {process.pid}")
            
            # Convert to async-compatible object for monitoring
            class AsyncProcess:
                def __init__(self, popen_process):
                    self.process = popen_process
                    self.pid = popen_process.pid
                    self.returncode = None
                
                async def wait(self):
                    # Poll until process completes
                    while self.process.poll() is None:
                        await asyncio.sleep(0.1)
                    self.returncode = self.process.returncode
                    return self.returncode
                
                def terminate(self):
                    self.process.terminate()
                
                def kill(self):
                    self.process.kill()
                
                async def communicate(self):
                    # Run communicate in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    stdout, stderr = await loop.run_in_executor(None, self.process.communicate)
                    return stdout.encode() if stdout else b"", stderr.encode() if stderr else b""
            
            # Wrap the process for async compatibility
            async_process = AsyncProcess(process)
            
        except FileNotFoundError as e:
            error_msg = f"Training script not found: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Training script not found"
            training_sessions[session_id]["error"] = error_msg
            training_sessions[session_id]["end_time"] = datetime.now()
            return
        except PermissionError as e:
            error_msg = f"Permission denied: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Permission denied when starting training"
            training_sessions[session_id]["error"] = error_msg
            training_sessions[session_id]["end_time"] = datetime.now()
            return
        except Exception as e:
            error_msg = f"Failed to start subprocess: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Exception details: {repr(e)}")
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Failed to start training process"
            training_sessions[session_id]["error"] = error_msg
            training_sessions[session_id]["end_time"] = datetime.now()
            return
        
        # Store process reference for potential termination (not in main session data to avoid JSON serialization issues)
        training_sessions[session_id]["_process"] = async_process  # Use underscore prefix to indicate internal use
        
        # Monitor training output for progress updates
        logger.info("Starting background monitoring task...")
        
        async def monitor_training_output():
            """Monitor training output and update progress in real-time"""
            try:
                import select
                import sys
                
                # Set up non-blocking reading for Windows compatibility
                if sys.platform == "win32":
                    # Windows approach - use threading for real-time output
                    import threading
                    import queue
                    
                    output_queue = queue.Queue()
                    
                    def read_output():
                        try:
                            for line in iter(async_process.process.stdout.readline, ''):
                                if line:
                                    output_queue.put(line.strip())
                                else:
                                    break
                        except Exception as e:
                            logger.error(f"Error in output reader thread: {e}")
                    
                    # Start reader thread
                    reader_thread = threading.Thread(target=read_output, daemon=True)
                    reader_thread.start()
                    
                    while async_process.process.poll() is None:
                        # Check if training was stopped
                        if training_sessions[session_id]["status"] == "stopped":
                            async_process.terminate()
                            training_sessions[session_id]["message"] = "Training stopped by user"
                            training_sessions[session_id]["end_time"] = datetime.now()
                            return
                        
                        # Read available output
                        try:
                            while not output_queue.empty():
                                output_text = output_queue.get_nowait()
                                if output_text:
                                    logger.info(f"Training output: {output_text}")
                                    
                                    # Update progress based on output
                                    if output_text and ("epoch" in output_text.lower() or "training" in output_text.lower() or "installing" in output_text.lower()):
                                        update_progress_from_output(session_id, output_text)
                                    
                                    # Update status based on key phrases
                                    if "Loading model" in output_text:
                                        training_sessions[session_id]["message"] = "Loading model..."
                                    elif "Starting LoRA Training" in output_text:
                                        training_sessions[session_id]["message"] = "Training started..."
                                    elif "Training Completed" in output_text:
                                        training_sessions[session_id]["message"] = "Training completed!"
                                        training_sessions[session_id]["progress"] = 100.0
                        
                        except queue.Empty:
                            pass
                        except Exception as e:
                            logger.debug(f"Error reading output: {e}")
                        
                        # Small delay to prevent busy waiting
                        await asyncio.sleep(0.1)
                
                else:
                    # Unix/Linux approach - use select
                    while async_process.process.poll() is None:
                        # Check if training was stopped
                        if training_sessions[session_id]["status"] == "stopped":
                            async_process.terminate()
                            training_sessions[session_id]["message"] = "Training stopped by user"
                            training_sessions[session_id]["end_time"] = datetime.now()
                            return
                        
                        # Use select for non-blocking read
                        ready, _, _ = select.select([async_process.process.stdout], [], [], 0.1)
                        if ready:
                            line = async_process.process.stdout.readline()
                            if line:
                                output_text = line.strip()
                                logger.info(f"Training output: {output_text}")
                                
                                # Update progress based on output
                                if output_text and ("epoch" in output_text.lower() or "training" in output_text.lower()):
                                    update_progress_from_output(session_id, output_text)
                                
                                # Update status based on key phrases
                                if "Loading model" in output_text:
                                    training_sessions[session_id]["message"] = "Loading model..."
                                elif "Starting LoRA Training" in output_text:
                                    training_sessions[session_id]["message"] = "Training started..."
                                elif "Training Completed" in output_text:
                                    training_sessions[session_id]["message"] = "Training completed!"
                                    training_sessions[session_id]["progress"] = 100.0
                        
                        await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error monitoring training output: {e}")
        
        # Start monitoring task
        monitor_task = asyncio.create_task(monitor_training_output())
        
        # Wait for process completion with timeout
        try:
            return_code = await asyncio.wait_for(async_process.wait(), timeout=14400.0)  # 4 hours max for large models
        except asyncio.TimeoutError:
            logger.error("Training process timed out after 4 hours")
            async_process.kill()
            training_sessions[session_id]["status"] = "failed"
            training_sessions[session_id]["message"] = "Training timed out"
            training_sessions[session_id]["error"] = "Process exceeded 4 hour time limit"
            training_sessions[session_id]["end_time"] = datetime.now()
            return
        finally:
            # Cancel monitoring task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # Process completed, get final output
        try:
            stdout, stderr = await async_process.communicate()
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            # Log the output for debugging
            if stdout_text:
                logger.info(f"Training stdout: {stdout_text[:1000]}...")  # First 1000 chars
            if stderr_text:
                logger.error(f"Training stderr: {stderr_text}")
                
        except Exception as e:
            logger.error(f"Error getting process output: {e}")
            stdout_text = ""
            stderr_text = str(e)
        
        logger.info(f"Process completed with return code: {return_code}")
        
        if return_code == 0:
            # Training completed successfully
            training_sessions[session_id]["status"] = "completed"
            training_sessions[session_id]["progress"] = 100.0
            training_sessions[session_id]["message"] = "Training completed successfully!"
            training_sessions[session_id]["end_time"] = datetime.now()
            
            # Parse final result
            try:
                result = json.loads(stdout_text)
                if result.get("success"):
                    training_sessions[session_id]["message"] = result.get("message", "Training completed!")
            except:
                pass
                
        else:
            # Training failed
            training_sessions[session_id]["status"] = "failed"
            
            # Provide more detailed error message
            if stderr_text:
                training_sessions[session_id]["message"] = f"Training failed: {stderr_text[:200]}"
                training_sessions[session_id]["error"] = stderr_text
            elif return_code == 1:
                training_sessions[session_id]["message"] = "Training script execution failed"
                training_sessions[session_id]["error"] = "Script exited with code 1. Check dependencies and model availability."
            else:
                training_sessions[session_id]["message"] = f"Training failed with exit code {return_code}"
                training_sessions[session_id]["error"] = f"Process exited with code {return_code}"
                
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
        output_lower = output.lower()
        
        # Parse epoch information - handle multiple formats
        if "epoch" in output_lower:
            import re
            
            # Try different epoch patterns
            # Pattern 1: "Epoch 1/3" or "epoch 1/3"
            epoch_match = re.search(r'epoch\s*(\d+)[/:](\d+)', output_lower)
            if epoch_match:
                current = int(epoch_match.group(1))
                total = int(epoch_match.group(2))
                training_sessions[session_id]["current_epoch"] = current
                training_sessions[session_id]["total_epochs"] = total
                
                # Calculate progress
                progress = (current / total) * 100
                training_sessions[session_id]["progress"] = min(progress, 100.0)
                logger.info(f"Progress updated: Epoch {current}/{total} ({progress:.1f}%)")
            
            # Pattern 2: Look for step progress within epochs
            step_match = re.search(r'(\d+)/(\d+)', output)
            if step_match and not epoch_match:  # Only if we didn't find epoch info
                current_step = int(step_match.group(1))
                total_steps = int(step_match.group(2))
                
                # Estimate progress within current epoch
                current_epoch = training_sessions[session_id].get("current_epoch", 0)
                total_epochs = training_sessions[session_id].get("total_epochs", 3)
                
                if total_epochs > 0:
                    epoch_progress = (current_step / total_steps) * (100 / total_epochs)
                    base_progress = (current_epoch / total_epochs) * 100
                    total_progress = base_progress + epoch_progress
                    training_sessions[session_id]["progress"] = min(total_progress, 100.0)
        
        # Parse loss values - handle multiple formats
        if "loss" in output_lower:
            import re
            # Try different loss patterns
            loss_patterns = [
                r'loss[:\s]*([0-9.]+)',
                r'training_loss[:\s]*([0-9.]+)',
                r'train_loss[:\s]*([0-9.]+)'
            ]
            
            for pattern in loss_patterns:
                loss_match = re.search(pattern, output_lower)
                if loss_match:
                    training_sessions[session_id]["train_loss"] = float(loss_match.group(1))
                    break
        
        # Update message based on training phases
        if "installing" in output_lower or "downloading" in output_lower:
            training_sessions[session_id]["message"] = "Installing dependencies..."
        elif "loading" in output_lower and "model" in output_lower:
            training_sessions[session_id]["message"] = "Loading model..."
        elif "tokenizing" in output_lower or "preparing" in output_lower:
            training_sessions[session_id]["message"] = "Preparing dataset..."
        elif "training" in output_lower and ("start" in output_lower or "begin" in output_lower):
            training_sessions[session_id]["message"] = "Training started..."
    
    except Exception as e:
        logger.warning(f"Error parsing training output '{output}': {e}")

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
