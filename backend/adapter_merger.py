#!/usr/bin/env python3
"""
Adapter Merger for Inference
Handles merging LoRA adapters with base models for inference
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdapterMerger:
    """Handle merging LoRA adapters with base models for inference"""
    
    def __init__(self):
        self.adapter_exports_dir = os.path.join(os.getcwd(), "adapter_exports")
        self.merged_models_dir = os.path.join(os.getcwd(), "merged_models")
        
        # Ensure directories exist
        os.makedirs(self.merged_models_dir, exist_ok=True)
    
    def list_available_adapters(self) -> List[Dict[str, Any]]:
        """List all available adapters"""
        adapters = []
        
        if not os.path.exists(self.adapter_exports_dir):
            logger.warning("No adapter exports directory found")
            return adapters
        
        for item in os.listdir(self.adapter_exports_dir):
            if item.startswith("adapter_export_"):
                adapter_path = os.path.join(self.adapter_exports_dir, item)
                if os.path.isdir(adapter_path):
                    # Try to find adapter config
                    config_path = os.path.join(adapter_path, "adapter_config.json")
                    if os.path.exists(config_path):
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                            
                            adapters.append({
                                "export_id": item,
                                "adapter_name": config.get("adapter_name", "unknown"),
                                "base_model": config.get("base_model", "unknown"),
                                "created_at": config.get("created_at", "unknown"),
                                "path": adapter_path,
                                "config": config
                            })
                        except Exception as e:
                            logger.error(f"Error reading config for {item}: {e}")
                    else:
                        # Fallback: create basic info from directory name
                        adapters.append({
                            "export_id": item,
                            "adapter_name": "unknown",
                            "base_model": "unknown", 
                            "created_at": "unknown",
                            "path": adapter_path,
                            "config": {}
                        })
        
        return sorted(adapters, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def get_adapter_info(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific adapter"""
        adapters = self.list_available_adapters()
        for adapter in adapters:
            if adapter["export_id"] == adapter_id:
                return adapter
        return None
    
    def merge_adapter_with_model(self, adapter_id: str, base_model: str = None) -> Dict[str, Any]:
        """
        Merge a LoRA adapter with a base model for inference
        
        Args:
            adapter_id: The adapter export ID to merge
            base_model: Optional base model name (if not provided, uses adapter's base model)
            
        Returns:
            Dict with merge status and information
        """
        try:
            # Get adapter information
            adapter_info = self.get_adapter_info(adapter_id)
            if not adapter_info:
                return {
                    "success": False,
                    "error": f"Adapter {adapter_id} not found"
                }
            
            # Use provided base model or adapter's base model
            if not base_model:
                base_model = adapter_info["base_model"]
            
            if not base_model or base_model == "unknown":
                return {
                    "success": False,
                    "error": "Base model not specified and not found in adapter config"
                }
            
            # Create merged model directory
            merged_model_name = f"{adapter_info['adapter_name']}_merged_{int(time.time())}"
            merged_model_path = os.path.join(self.merged_models_dir, merged_model_name)
            os.makedirs(merged_model_path, exist_ok=True)
            
            # Create merge script
            merge_script = self._create_merge_script(
                adapter_info["path"],
                base_model,
                merged_model_path
            )
            
            # Execute merge
            logger.info(f"Starting merge of adapter {adapter_id} with base model {base_model}")
            result = self._execute_merge_script(merge_script)
            
            if result["success"]:
                # Create merged model info
                merged_info = {
                    "merged_model_name": merged_model_name,
                    "merged_model_path": merged_model_path,
                    "adapter_id": adapter_id,
                    "adapter_name": adapter_info["adapter_name"],
                    "base_model": base_model,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "ready"
                }
                
                # Save merged model info
                info_path = os.path.join(merged_model_path, "merged_model_info.json")
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(merged_info, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Successfully merged adapter. Merged model saved to: {merged_model_path}")
                
                return {
                    "success": True,
                    "merged_model_name": merged_model_name,
                    "merged_model_path": merged_model_path,
                    "adapter_info": adapter_info,
                    "base_model": base_model,
                    "message": "Adapter successfully merged with base model"
                }
            else:
                return {
                    "success": False,
                    "error": result["error"]
                }
                
        except Exception as e:
            logger.error(f"Error merging adapter {adapter_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_merge_script(self, adapter_path: str, base_model: str, output_path: str) -> str:
        """Create a script to merge the adapter with the base model"""
        
        # Find the adapter directory within the export
        adapter_dir = os.path.join(adapter_path, "adapter")
        if not os.path.exists(adapter_dir):
            adapter_dir = adapter_path  # Fallback to export path
        
        script_content = f'''#!/usr/bin/env python3
"""
Auto-generated script to merge LoRA adapter with base model
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        # Import required libraries
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        
        # Configuration
        base_model = "{base_model}"
        adapter_path = r"{adapter_dir}"
        output_path = r"{output_path}"
        
        logger.info(f"Loading base model: {{base_model}}")
        
        # Load base model and tokenizer
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype="auto",
            device_map="auto"
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model)
        
        logger.info(f"Loading LoRA adapter from: {{adapter_path}}")
        
        # Load LoRA adapter
        model = PeftModel.from_pretrained(model, adapter_path)
        
        logger.info("Merging adapter with base model...")
        
        # Merge adapter with base model
        merged_model = model.merge_and_unload()
        
        logger.info(f"Saving merged model to: {{output_path}}")
        
        # Save merged model
        merged_model.save_pretrained(output_path, safe_serialization=True)
        tokenizer.save_pretrained(output_path)
        
        # Create model info
        model_info = {{
            "base_model": base_model,
            "adapter_path": adapter_path,
            "merged_at": "{time.strftime('%Y-%m-%d %H:%M:%S')}",
            "model_type": "merged_lora",
            "status": "ready"
        }}
        
        with open(os.path.join(output_path, "model_info.json"), 'w', encoding='utf-8') as f:
            json.dump(model_info, f, indent=2, ensure_ascii=False)
        
        logger.info("Model merge completed successfully!")
        print("{{"success": true, "message": "Model merge completed successfully"}}")
        
    except Exception as e:
        logger.error(f"Error during model merge: {{e}}")
        print("{{"success": false, "error": str(e)}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        return script_content
    
    def _execute_merge_script(self, script_content: str) -> Dict[str, Any]:
        """Execute the merge script and return results"""
        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(script_content)
                script_path = f.name
            
            # Execute the script
            logger.info("Executing model merge script...")
            result = subprocess.run([
                sys.executable, script_path
            ], capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            # Clean up script file
            os.unlink(script_path)
            
            if result.returncode == 0:
                # Try to parse JSON output
                try:
                    output_lines = result.stdout.strip().split('\n')
                    json_output = None
                    for line in reversed(output_lines):
                        if line.strip().startswith('{') and line.strip().endswith('}'):
                            json_output = json.loads(line.strip())
                            break
                    
                    if json_output and json_output.get("success"):
                        return {"success": True, "output": result.stdout}
                    else:
                        return {"success": False, "error": json_output.get("error", "Unknown error")}
                except:
                    # If JSON parsing fails, check if merge was successful
                    if "Model merge completed successfully" in result.stdout:
                        return {"success": True, "output": result.stdout}
                    else:
                        return {"success": False, "error": "Merge script execution failed"}
            else:
                return {
                    "success": False,
                    "error": f"Script execution failed with return code {result.returncode}",
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Merge script timed out after 1 hour"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_merged_models(self) -> List[Dict[str, Any]]:
        """List all merged models"""
        merged_models = []
        
        if not os.path.exists(self.merged_models_dir):
            return merged_models
        
        for item in os.listdir(self.merged_models_dir):
            model_path = os.path.join(self.merged_models_dir, item)
            if os.path.isdir(model_path):
                info_path = os.path.join(model_path, "merged_model_info.json")
                if os.path.exists(info_path):
                    try:
                        with open(info_path, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        merged_models.append(info)
                    except Exception as e:
                        logger.error(f"Error reading merged model info for {item}: {e}")
        
        return sorted(merged_models, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def delete_merged_model(self, merged_model_name: str) -> Dict[str, Any]:
        """Delete a merged model"""
        try:
            model_path = os.path.join(self.merged_models_dir, merged_model_name)
            if os.path.exists(model_path):
                shutil.rmtree(model_path)
                return {"success": True, "message": f"Merged model {merged_model_name} deleted successfully"}
            else:
                return {"success": False, "error": f"Merged model {merged_model_name} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def register_merged_model_with_ollama(self, merged_model_name: str) -> Dict[str, Any]:
        """Register a merged model with Ollama for inference"""
        try:
            model_path = os.path.join(self.merged_models_dir, merged_model_name)
            if not os.path.exists(model_path):
                return {"success": False, "error": f"Merged model {merged_model_name} not found"}
            
            # Create Ollama Modelfile for the merged model
            modelfile_path = os.path.join(model_path, "Modelfile")
            self._create_ollama_modelfile(model_path, modelfile_path, merged_model_name)
            
            # Create Ollama model
            ollama_model_name = f"{merged_model_name}_ollama"
            result = self._create_ollama_model(model_path, ollama_model_name)
            
            if result["success"]:
                # Update merged model info
                info_path = os.path.join(model_path, "merged_model_info.json")
                if os.path.exists(info_path):
                    with open(info_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    info["ollama_model_name"] = ollama_model_name
                    info["ollama_registered"] = True
                    with open(info_path, 'w', encoding='utf-8') as f:
                        json.dump(info, f, indent=2, ensure_ascii=False)
                
                return {
                    "success": True,
                    "ollama_model_name": ollama_model_name,
                    "message": f"Merged model registered with Ollama as {ollama_model_name}"
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_ollama_modelfile(self, model_path: str, modelfile_path: str, model_name: str):
        """Create Ollama Modelfile for the merged model"""
        modelfile_content = f'''# Modelfile for merged LoRA model: {model_name}
FROM {model_path}

# System prompt for Cantonese travel content generation
SYSTEM """你是一個專門生成粵語旅遊內容的AI助手。你的任務是根據提供的機票資料，生成結構化的JSON格式旅遊內容。

請按照以下格式輸出JSON：
{{
  "Destination": "目的地",
  "Header": "吸引人的標題",
  "Short Comment": "簡短評論",
  "Summary": "詳細摘要"
}}

要求：
1. 使用粵語表達方式
2. 內容要生動有趣
3. 突出旅遊的吸引點
4. 確保JSON格式完整
5. 只輸出JSON，不要添加其他文字"""

# Template for user input
TEMPLATE """{{{{ if .System }}}}{{{{ .System }}}}{{{{ end }}}}{{{{ if .Prompt }}}}{{{{ .Prompt }}}}{{{{ end }}}}"""

# Parameters for better output
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER stop "}}"
'''
        
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
    
    def _create_ollama_model(self, model_path: str, ollama_model_name: str) -> Dict[str, Any]:
        """Create Ollama model from merged model"""
        try:
            modelfile_path = os.path.join(model_path, "Modelfile")
            if not os.path.exists(modelfile_path):
                return {"success": False, "error": "Modelfile not found"}
            
            # Create Ollama model
            logger.info(f"Creating Ollama model: {ollama_model_name}")
            result = subprocess.run([
                "ollama", "create", "-f", modelfile_path, ollama_model_name
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Successfully created Ollama model: {ollama_model_name}")
                return {"success": True, "message": f"Ollama model {ollama_model_name} created successfully"}
            else:
                logger.error(f"Failed to create Ollama model: {result.stderr}")
                return {"success": False, "error": f"Ollama model creation failed: {result.stderr}"}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Ollama model creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_inference_endpoint(self, merged_model_name: str) -> Dict[str, Any]:
        """Get inference endpoint information for a merged model"""
        try:
            model_path = os.path.join(self.merged_models_dir, merged_model_name)
            if not os.path.exists(model_path):
                return {"success": False, "error": f"Merged model {merged_model_name} not found"}
            
            info_path = os.path.join(model_path, "merged_model_info.json")
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                # Check if registered with Ollama
                if info.get("ollama_registered", False):
                    ollama_model_name = info.get("ollama_model_name", merged_model_name)
                    return {
                        "success": True,
                        "model_name": merged_model_name,
                        "ollama_model_name": ollama_model_name,
                        "inference_type": "ollama",
                        "endpoint": f"http://localhost:11434/api/generate",
                        "model_path": model_path,
                        "ready_for_inference": True
                    }
                else:
                    return {
                        "success": True,
                        "model_name": merged_model_name,
                        "inference_type": "direct",
                        "model_path": model_path,
                        "ready_for_inference": True,
                        "note": "Model not registered with Ollama yet"
                    }
            else:
                return {"success": False, "error": "Model info not found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

def main():
    """Command line interface for adapter merger"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adapter Merger for Inference")
    parser.add_argument("--list-adapters", action="store_true", help="List available adapters")
    parser.add_argument("--list-merged", action="store_true", help="List merged models")
    parser.add_argument("--merge", help="Merge adapter with base model (provide adapter ID)")
    parser.add_argument("--base-model", help="Base model to merge with")
    parser.add_argument("--delete-merged", help="Delete a merged model")
    
    args = parser.parse_args()
    
    merger = AdapterMerger()
    
    if args.list_adapters:
        adapters = merger.list_available_adapters()
        print(f"Found {len(adapters)} available adapters:")
        for adapter in adapters:
            print(f"  - {adapter['export_id']}: {adapter['adapter_name']} (base: {adapter['base_model']})")
    
    elif args.list_merged:
        merged_models = merger.list_merged_models()
        print(f"Found {len(merged_models)} merged models:")
        for model in merged_models:
            print(f"  - {model['merged_model_name']}: {model['adapter_name']} + {model['base_model']}")
    
    elif args.merge:
        result = merger.merge_adapter_with_model(args.merge, args.base_model)
        if result["success"]:
            print(f"✅ Successfully merged adapter {args.merge}")
            print(f"   Merged model: {result['merged_model_name']}")
            print(f"   Path: {result['merged_model_path']}")
        else:
            print(f"❌ Failed to merge adapter: {result['error']}")
            sys.exit(1)
    
    elif args.delete_merged:
        result = merger.delete_merged_model(args.delete_merged)
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
            sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
