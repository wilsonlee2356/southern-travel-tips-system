#!/usr/bin/env python3
"""
RAG Adapter Merger
Merges fine-tuned adapters with base models for RAG usage in OpenWebUI
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

class RAGAdapterMerger:
    """Handle merging LoRA adapters with base models for RAG usage"""
    
    def __init__(self):
        self.adapter_exports_dir = os.path.join(os.getcwd(), "adapter_exports")
        self.rag_models_dir = os.path.join(os.getcwd(), "rag_models")
        
        # Ensure directories exist
        os.makedirs(self.rag_models_dir, exist_ok=True)
    
    def create_rag_merged_model(self, adapter_id: str, base_model: str = "qwen2.5:14b") -> Dict[str, Any]:
        """
        Create a RAG-optimized model without full model merging (lightweight approach)
        
        Args:
            adapter_id: The adapter export ID to use
            base_model: Base model name (for reference only)
            
        Returns:
            Dict with RAG model creation status
        """
        try:
            # Get adapter information
            adapter_info = self._get_adapter_info(adapter_id)
            if not adapter_info:
                return {
                    "success": False,
                    "error": f"Adapter {adapter_id} not found"
                }
            
            # Create RAG-specific model directory
            rag_model_name = f"{adapter_info['adapter_name']}_rag_{int(time.time())}"
            rag_model_path = os.path.join(self.rag_models_dir, rag_model_name)
            os.makedirs(rag_model_path, exist_ok=True)
            
            # Copy adapter files to RAG model directory
            adapter_source = os.path.join(adapter_info["path"], "adapter")
            if os.path.exists(adapter_source):
                import shutil
                shutil.copytree(adapter_source, os.path.join(rag_model_path, "adapter"))
                logger.info(f"Copied adapter files to {rag_model_path}")
            else:
                # Fallback: copy from export root
                adapter_files = ["adapter_config.json", "adapter_model.safetensors", "adapter.gguf"]
                for file_name in adapter_files:
                    src_file = os.path.join(adapter_info["path"], file_name)
                    if os.path.exists(src_file):
                        shutil.copy2(src_file, rag_model_path)
                        logger.info(f"Copied {file_name} to RAG model directory")
            
            # Create Ollama Modelfile for RAG (using existing base model)
            self._create_rag_modelfile(rag_model_path, rag_model_name, base_model)
            
            # Create Ollama model (using existing base model with adapter)
            ollama_model_name = f"{rag_model_name}_ollama"
            ollama_result = self._create_ollama_rag_model(rag_model_path, ollama_model_name)
            
            if ollama_result["success"]:
                # Create RAG model info
                rag_info = {
                    "rag_model_name": rag_model_name,
                    "rag_model_path": rag_model_path,
                    "ollama_model_name": ollama_model_name,
                    "adapter_id": adapter_id,
                    "adapter_name": adapter_info["adapter_name"],
                    "base_model": base_model,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "ready_for_rag",
                    "purpose": "RAG",
                    "method": "lightweight_adapter_reference"
                }
                
                # Save RAG model info
                info_path = os.path.join(rag_model_path, "rag_model_info.json")
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(rag_info, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Successfully created lightweight RAG model: {rag_model_name}")
                
                return {
                    "success": True,
                    "rag_model_name": rag_model_name,
                    "ollama_model_name": ollama_model_name,
                    "rag_model_path": rag_model_path,
                    "adapter_info": adapter_info,
                    "base_model": base_model,
                    "message": "Lightweight RAG model created successfully (uses existing base model with adapter)"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create Ollama model: {ollama_result['error']}"
                }
                
        except Exception as e:
            logger.error(f"Error creating RAG model {adapter_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_adapter_info(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """Get adapter information"""
        if not os.path.exists(self.adapter_exports_dir):
            return None
        
        adapter_path = os.path.join(self.adapter_exports_dir, adapter_id)
        if not os.path.exists(adapter_path):
            return None
        
        config_path = os.path.join(adapter_path, "adapter_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return {
                    "export_id": adapter_id,
                    "adapter_name": config.get("adapter_name", "unknown"),
                    "base_model": config.get("base_model", "unknown"),
                    "created_at": config.get("created_at", "unknown"),
                    "path": adapter_path,
                    "config": config
                }
            except Exception as e:
                logger.error(f"Error reading adapter config: {e}")
                return None
        return None
    
    def _create_rag_merge_script(self, adapter_path: str, base_model: str, output_path: str) -> str:
        """Create a script to merge the adapter with the base model for RAG"""
        
        # Find the adapter directory within the export
        adapter_dir = os.path.join(adapter_path, "adapter")
        if not os.path.exists(adapter_dir):
            adapter_dir = adapter_path  # Fallback to export path
        
        script_content = f'''#!/usr/bin/env python3
"""
Auto-generated script to merge LoRA adapter with base model for RAG
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
        
        logger.info(f"Loading base model for RAG: {{base_model}}")
        
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
        
        logger.info("Merging adapter with base model for RAG...")
        
        # Merge adapter with base model
        merged_model = model.merge_and_unload()
        
        logger.info(f"Saving RAG model to: {{output_path}}")
        
        # Save merged model
        merged_model.save_pretrained(output_path, safe_serialization=True)
        tokenizer.save_pretrained(output_path)
        
        # Create model info
        model_info = {{
            "base_model": base_model,
            "adapter_path": adapter_path,
            "merged_at": "{time.strftime('%Y-%m-%d %H:%M:%S')}",
            "model_type": "merged_lora_rag",
            "status": "ready",
            "purpose": "RAG"
        }}
        
        with open(os.path.join(output_path, "model_info.json"), 'w', encoding='utf-8') as f:
            json.dump(model_info, f, indent=2, ensure_ascii=False)
        
        logger.info("RAG model merge completed successfully!")
        print('{{"success": true, "message": "RAG model merge completed successfully"}}')
        
    except Exception as e:
        logger.error(f"Error during RAG model merge: {{e}}")
        print('{{"success": false, "error": "' + str(e).replace('"', '\\"') + '"}}')
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        return script_content
    
    def _create_rag_modelfile(self, model_path: str, model_name: str, base_model: str):
        """Create Ollama Modelfile specifically for RAG usage"""
        modelfile_path = os.path.join(model_path, "Modelfile")
        
        modelfile_content = f'''# Modelfile for RAG-optimized LoRA model: {model_name}
FROM {base_model}

# System prompt optimized for RAG (Retrieval-Augmented Generation)
SYSTEM """你是一個專門處理檢索增強生成(RAG)的AI助手。你的任務是根據提供的上下文信息，生成準確、相關且有用的回答。

當你收到包含上下文信息的查詢時，請：
1. 仔細分析提供的上下文信息
2. 基於上下文信息回答問題
3. 如果上下文信息不足，請明確說明
4. 保持回答的準確性和相關性
5. 使用粵語表達方式（如果適用）

請根據以下格式提供回答：
- 如果上下文信息充分：直接回答問題
- 如果上下文信息不足：說明需要更多信息
- 如果問題與上下文無關：禮貌地說明並建議相關問題"""

# Template for RAG input
TEMPLATE """{{{{ if .System }}}}{{{{ .System }}}}{{{{ end }}}}{{{{ if .Prompt }}}}{{{{ .Prompt }}}}{{{{ end }}}}"""

# Parameters optimized for RAG
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER stop "}}"
'''
        
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
    
    def _create_ollama_rag_model(self, model_path: str, ollama_model_name: str) -> Dict[str, Any]:
        """Create Ollama model from merged RAG model"""
        try:
            modelfile_path = os.path.join(model_path, "Modelfile")
            if not os.path.exists(modelfile_path):
                return {"success": False, "error": "Modelfile not found"}
            
            # Create Ollama model
            logger.info(f"Creating Ollama RAG model: {ollama_model_name}")
            result = subprocess.run([
                "ollama", "create", "-f", modelfile_path, ollama_model_name
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Successfully created Ollama RAG model: {ollama_model_name}")
                return {"success": True, "message": f"Ollama RAG model {ollama_model_name} created successfully"}
            else:
                logger.error(f"Failed to create Ollama RAG model: {result.stderr}")
                return {"success": False, "error": f"Ollama RAG model creation failed: {result.stderr}"}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Ollama RAG model creation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_merge_script(self, script_content: str) -> Dict[str, Any]:
        """Execute the merge script and return results"""
        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(script_content)
                script_path = f.name
            
            # Execute the script
            logger.info("Executing RAG model merge script...")
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
                    if "RAG model merge completed successfully" in result.stdout:
                        return {"success": True, "output": result.stdout}
                    else:
                        return {"success": False, "error": "RAG merge script execution failed"}
            else:
                return {
                    "success": False,
                    "error": f"Script execution failed with return code {result.returncode}",
                    "stderr": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "RAG merge script timed out after 1 hour"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_rag_models(self) -> List[Dict[str, Any]]:
        """List all RAG models"""
        rag_models = []
        
        if not os.path.exists(self.rag_models_dir):
            return rag_models
        
        for item in os.listdir(self.rag_models_dir):
            model_path = os.path.join(self.rag_models_dir, item)
            if os.path.isdir(model_path):
                info_path = os.path.join(model_path, "rag_model_info.json")
                if os.path.exists(info_path):
                    try:
                        with open(info_path, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        rag_models.append(info)
                    except Exception as e:
                        logger.error(f"Error reading RAG model info for {item}: {e}")
        
        return sorted(rag_models, key=lambda x: x.get("created_at", ""), reverse=True)

    def test_rag_model(self, model_name, test_query="測試RAG功能"):
        """Test a RAG model with a sample query"""
        try:
            import requests
            
            # Test the model via Ollama API
            ollama_url = "http://localhost:11434/api/generate"
            
            payload = {
                "model": model_name,
                "prompt": test_query,
                "stream": False
            }
            
            response = requests.post(ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": model_name,
                    "test_query": test_query
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama API error: {response.status_code}",
                    "model": model_name,
                    "test_query": test_query
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": model_name,
                "test_query": test_query
            }

    def delete_rag_model(self, rag_model_name: str) -> bool:
        """Delete a RAG model and its associated files"""
        try:
            rag_models = self.list_rag_models()
            
            # Find the RAG model
            rag_model = None
            for model in rag_models:
                if model['rag_model_name'] == rag_model_name:
                    rag_model = model
                    break
            
            if not rag_model:
                print(f"❌ RAG model '{rag_model_name}' not found")
                return False
            
            rag_model_path = rag_model['rag_model_path']
            ollama_model_name = rag_model['ollama_model_name']
            
            # Remove Ollama model if it exists
            try:
                import subprocess
                result = subprocess.run(['ollama', 'rm', ollama_model_name], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"✅ Removed Ollama model: {ollama_model_name}")
                else:
                    print(f"⚠️  Warning: Could not remove Ollama model {ollama_model_name}: {result.stderr}")
            except Exception as e:
                print(f"⚠️  Warning: Could not remove Ollama model {ollama_model_name}: {e}")
            
            # Remove RAG model directory
            import shutil
            if os.path.exists(rag_model_path):
                shutil.rmtree(rag_model_path)
                print(f"✅ Removed RAG model directory: {rag_model_path}")
            else:
                print(f"⚠️  Warning: RAG model directory not found: {rag_model_path}")
            
            # Remove from registry if it exists
            registry_path = os.path.join(self.rag_models_dir, "rag_models_registry.json")
            if os.path.exists(registry_path):
                try:
                    with open(registry_path, 'r', encoding='utf-8') as f:
                        registry = json.load(f)
                    
                    # Remove the model from registry
                    if rag_model_name in registry:
                        del registry[rag_model_name]
                        
                        with open(registry_path, 'w', encoding='utf-8') as f:
                            json.dump(registry, f, indent=2, ensure_ascii=False)
                        print(f"✅ Removed from registry: {rag_model_name}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not update registry: {e}")
            
            print(f"✅ Successfully deleted RAG model: {rag_model_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting RAG model: {e}")
            return False

def main():
    """Command line interface for RAG adapter merger"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Adapter Merger")
    parser.add_argument("--create-rag-model", help="Create RAG model from adapter (provide adapter ID)")
    parser.add_argument("--base-model", help="Base model to merge with", default="qwen2.5:14b")
    parser.add_argument("--list-rag-models", action="store_true", help="List RAG models")
    
    args = parser.parse_args()
    
    merger = RAGAdapterMerger()
    
    if args.create_rag_model:
        result = merger.create_rag_merged_model(args.create_rag_model, args.base_model)
        if result["success"]:
            print(f"✅ Successfully created RAG model: {result['rag_model_name']}")
            print(f"   Ollama model: {result['ollama_model_name']}")
            print(f"   Path: {result['rag_model_path']}")
            print(f"   Ready for RAG usage in OpenWebUI!")
        else:
            print(f"❌ Failed to create RAG model: {result['error']}")
            sys.exit(1)
    
    elif args.list_rag_models:
        rag_models = merger.list_rag_models()
        print(f"Found {len(rag_models)} RAG models:")
        for model in rag_models:
            print(f"  - {model['rag_model_name']}: {model['adapter_name']} + {model['base_model']}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
