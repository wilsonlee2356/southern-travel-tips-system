# RAG Integration Guide: Using Fine-tuned Adapters with OpenWebUI RAG

## Overview
This guide shows you how to merge your fine-tuned LoRA adapters with the base model (qwen2.5:14b) to create RAG-optimized models that can be used in OpenWebUI's RAG system.

## Prerequisites
- ✅ Fine-tuned adapter available (e.g., `adapter_export_training_1758890353`)
- ✅ Ollama running with qwen2.5:14b model
- ✅ OpenWebUI running with RAG enabled

## Step 1: Create RAG-Optimized Model

### Using Command Line:
```bash
# Create RAG model from your adapter
python rag_adapter_merger.py --create-rag-model adapter_export_training_1758890353 --base-model qwen2.5:14b

# List available RAG models
python rag_adapter_merger.py --list-rag-models
```

### Using API:
```bash
# Create RAG model via API
curl -X POST http://localhost:8001/api/rag/create-model \
  -H "Content-Type: application/json" \
  -d '{
    "adapter_id": "adapter_export_training_1758890353",
    "base_model": "qwen2.5:14b"
  }'

# List RAG models
curl http://localhost:8001/api/rag/models/list
```

## Step 2: Configure OpenWebUI for RAG

### Option A: Use the New RAG Model Directly
1. **In OpenWebUI Settings**:
   - Go to **Settings** → **RAG** → **Embedding Engine**
   - Set **Embedding Engine** to `ollama`
   - Set **Ollama Base URL** to `http://localhost:11434`
   - Set **Embedding Model** to your new RAG model (e.g., `my-custom-adapter_rag_1234567890_ollama`)

### Option B: Replace the Base Model
1. **Stop OpenWebUI** (if running)
2. **Replace the model in Ollama**:
   ```bash
   # Remove the old model (optional)
   ollama rm qwen2.5:14b
   
   # Pull your RAG model as qwen2.5:14b
   ollama pull my-custom-adapter_rag_1234567890_ollama
   ollama cp my-custom-adapter_rag_1234567890_ollama qwen2.5:14b
   ```
3. **Restart OpenWebUI**

## Step 3: Test RAG with Your Fine-tuned Model

### Upload Documents:
1. Go to **Knowledge** in OpenWebUI
2. Create a new collection
3. Upload your documents (PDF, TXT, etc.)
4. The system will use your fine-tuned model for embeddings and generation

### Test RAG:
1. Start a new chat
2. Ask questions about your uploaded documents
3. The system will:
   - Use your fine-tuned model for embeddings (if configured)
   - Use your fine-tuned model for generation
   - Provide context-aware responses in Cantonese

## Step 4: Verify Integration

### Check Model Usage:
```bash
# Check if your RAG model is available in Ollama
ollama list

# Test the model directly
ollama run my-custom-adapter_rag_1234567890_ollama "Test prompt"
```

### Monitor RAG Performance:
- Check OpenWebUI logs for RAG operations
- Verify that your fine-tuned model is being used
- Test with Cantonese content to see the improvement

## Benefits of This Integration

### 1. **Enhanced RAG Performance**:
- Your fine-tuned model understands Cantonese better
- More accurate embeddings for Cantonese documents
- Better context understanding for travel-related content

### 2. **Consistent Model Usage**:
- Same model for both fine-tuning and RAG
- Unified knowledge base with your specialized model
- Better coherence across different use cases

### 3. **Optimized for RAG**:
- System prompts optimized for RAG tasks
- Parameters tuned for retrieval and generation
- Better handling of context and citations

## Troubleshooting

### Common Issues:

1. **Model Not Found**:
   ```bash
   # Check if model exists
   ollama list
   
   # Recreate if needed
   python rag_adapter_merger.py --create-rag-model your_adapter_id
   ```

2. **RAG Not Working**:
   - Check OpenWebUI RAG settings
   - Verify Ollama is running
   - Check model compatibility

3. **Performance Issues**:
   - Ensure sufficient GPU memory
   - Check model size and requirements
   - Monitor system resources

## Advanced Configuration

### Custom RAG Templates:
You can modify the RAG system prompt in `rag_adapter_merger.py` to better suit your needs:

```python
# In _create_rag_modelfile method
SYSTEM """Your custom RAG system prompt here..."""
```

### Multiple RAG Models:
You can create multiple RAG models for different purposes:
- General RAG model
- Travel-specific RAG model
- Cantonese-optimized RAG model

## API Endpoints

### Available Endpoints:
- `POST /api/rag/create-model` - Create RAG model from adapter
- `GET /api/rag/models/list` - List available RAG models

### Example Usage:
```javascript
// Create RAG model
const response = await fetch('/api/rag/create-model', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    adapter_id: 'adapter_export_training_1758890353',
    base_model: 'qwen2.5:14b'
  })
});

const result = await response.json();
console.log('RAG model created:', result.ollama_model_name);
```

## Next Steps

1. **Create your RAG model** using the steps above
2. **Configure OpenWebUI** to use your model
3. **Upload documents** to your knowledge base
4. **Test RAG functionality** with Cantonese content
5. **Monitor performance** and adjust as needed

Your fine-tuned adapter is now integrated with OpenWebUI's RAG system! 🚀
