# Current RAG Configuration Analysis

## Current OpenWebUI RAG Setup

Based on the codebase analysis, here's what OpenWebUI is currently using for RAG:

### **Default Configuration**:
- **Embedding Engine**: Not set (empty string)
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (default)
- **Ollama Base URL**: Not set (uses default Ollama URL)
- **RAG Template**: Default template for context-aware responses

### **Current RAG Flow**:
1. **Document Processing**: Uses sentence-transformers for embeddings
2. **Vector Storage**: ChromaDB for storing embeddings
3. **Retrieval**: Similarity search with configurable top-k
4. **Generation**: Uses the chat model (qwen2.5:14b) for final response

## Integration Options for Your Fine-tuned Adapter

### **Option 1: Replace the Generation Model (Recommended)**

This is the easiest approach - keep the current embedding system but use your fine-tuned model for generation.

#### **Steps**:
1. **Create RAG-optimized model** from your adapter
2. **Replace the generation model** in OpenWebUI
3. **Keep existing embedding system** (sentence-transformers)

#### **Benefits**:
- ✅ **Minimal configuration changes**
- ✅ **Better Cantonese generation** with your fine-tuned model
- ✅ **Maintains existing document processing**
- ✅ **Easy to implement**

### **Option 2: Replace Both Embedding and Generation**

Use your fine-tuned model for both embeddings and generation.

#### **Steps**:
1. **Create RAG-optimized model** from your adapter
2. **Configure OpenWebUI** to use Ollama for embeddings
3. **Set your model** as both embedding and generation model

#### **Benefits**:
- ✅ **Consistent model usage** across RAG pipeline
- ✅ **Better Cantonese embeddings** for Cantonese documents
- ✅ **Unified model behavior**

### **Option 3: Hybrid Approach**

Use your fine-tuned model for generation and keep sentence-transformers for embeddings.

#### **Benefits**:
- ✅ **Best of both worlds**
- ✅ **Proven embedding system** (sentence-transformers)
- ✅ **Enhanced generation** with your model

## Implementation Guide

### **Step 1: Check Current RAG Status**

```bash
# Check what's currently configured
curl http://localhost:11434/api/tags  # Check Ollama models
curl http://localhost:3000/api/v1/rag/config  # Check OpenWebUI RAG config
```

### **Step 2: Create RAG-Optimized Model**

```bash
# Create RAG model from your adapter
python rag_adapter_merger.py --create-rag-model adapter_export_training_1758890353 --base-model qwen2.5:14b
```

### **Step 3: Configure OpenWebUI**

#### **For Option 1 (Generation Only)**:
1. Go to **OpenWebUI Settings** → **Models**
2. Add your new RAG model: `my-custom-adapter_rag_1234567890_ollama`
3. Use it for chat/generation
4. Keep current embedding settings

#### **For Option 2 (Full RAG)**:
1. Go to **OpenWebUI Settings** → **RAG**
2. Set **Embedding Engine** to `ollama`
3. Set **Embedding Model** to your RAG model
4. Set **Ollama Base URL** to `http://localhost:11434`

### **Step 4: Test RAG Integration**

1. **Upload a Cantonese document** to OpenWebUI
2. **Ask questions in Cantonese** about the document
3. **Verify** that your fine-tuned model is being used
4. **Check response quality** for Cantonese content

## Current RAG Architecture

```
Document Upload
     ↓
Text Extraction & Chunking
     ↓
Embedding Generation (sentence-transformers/all-MiniLM-L6-v2)
     ↓
Vector Storage (ChromaDB)
     ↓
Query Processing
     ↓
Similarity Search
     ↓
Context Retrieval
     ↓
Generation (qwen2.5:14b) ← Your fine-tuned model goes here
     ↓
Response with Citations
```

## Recommended Approach

**I recommend Option 1** for the following reasons:

1. **Minimal Risk**: Keeps the proven embedding system
2. **Easy Implementation**: Just replace the generation model
3. **Immediate Benefits**: Better Cantonese generation
4. **Backward Compatible**: Doesn't break existing functionality

### **Implementation Steps**:

1. **Create your RAG model**:
   ```bash
   python rag_adapter_merger.py --create-rag-model adapter_export_training_1758890353
   ```

2. **Add model to OpenWebUI**:
   - Go to Settings → Models
   - Add your RAG model
   - Use it for chat

3. **Test with RAG**:
   - Upload Cantonese documents
   - Ask questions in Cantonese
   - Verify improved responses

This approach gives you the benefits of your fine-tuned model while maintaining the stability of the existing RAG system.
