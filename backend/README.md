# LoRA Fine-tuning Backend

This backend provides real LoRA fine-tuning capabilities for Ollama models using Python and PyTorch.

## Features

- ✅ Real LoRA fine-tuning using PEFT (Parameter-Efficient Fine-Tuning)
- ✅ FastAPI backend with real-time progress monitoring
- ✅ Dataset validation and processing
- ✅ Automatic model registration with Ollama
- ✅ WebSocket-like progress updates via polling
- ✅ Support for JSON and JSONL datasets
- ✅ Comprehensive error handling and logging

## Prerequisites

1. **Python 3.8+** with pip
2. **Ollama** installed and running
3. **CUDA-capable GPU** (recommended for faster training)
4. **At least 8GB RAM** (16GB+ recommended)

## Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the backend server:
   ```bash
   python start_backend.py
   ```

   Or manually:
   ```bash
   python -m uvicorn fine_tuning_api:app --host 0.0.0.0 --port 8001 --reload
   ```

## API Endpoints

### Health Check
- `GET /health` - Check if the API is running

### Configuration
- `POST /api/fine-tuning/validate-config` - Validate training configuration
- `POST /api/fine-tuning/validate-dataset` - Validate uploaded dataset

### Training
- `POST /api/fine-tuning/start` - Start fine-tuning process
- `GET /api/fine-tuning/status/{session_id}` - Get training status
- `POST /api/fine-tuning/stop/{session_id}` - Stop training
- `GET /api/fine-tuning/sessions` - List all training sessions
- `DELETE /api/fine-tuning/session/{session_id}` - Delete training session

### Models
- `GET /api/models` - List available Ollama models

## Dataset Format

The backend supports two dataset formats:

### JSONL Format (Recommended)
```jsonl
{"prompt": "What is the capital of France?", "response": "The capital of France is Paris."}
{"prompt": "Explain photosynthesis", "response": "Photosynthesis is the process by which plants convert sunlight into energy."}
```

### JSON Format
```json
[
  {"prompt": "What is the capital of France?", "response": "The capital of France is Paris."},
  {"prompt": "Explain photosynthesis", "response": "Photosynthesis is the process by which plants convert sunlight into energy."}
]
```

## Training Configuration

```json
{
  "base_model": "qwen2.5:32b",
  "adapter_name": "my-custom-adapter",
  "learning_rate": 0.0001,
  "num_epochs": 3,
  "batch_size": 4,
  "gradient_accumulation_steps": 4,
  "lora_rank": 16,
  "lora_alpha": 32,
  "lora_dropout": 0.1,
  "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"]
}
```

## Usage Example

1. **Start the backend** (see Installation above)

2. **Upload a dataset** using the frontend interface

3. **Configure training parameters** in the UI

4. **Start training** - the system will:
   - Validate your dataset
   - Start the fine-tuning process
   - Provide real-time progress updates
   - Automatically register the new model with Ollama

5. **Use your fine-tuned model**:
   ```bash
   ollama run my-custom-adapter
   ```

## Technical Details

### LoRA Implementation
- Uses PEFT library for efficient fine-tuning
- Configurable LoRA rank, alpha, and dropout
- Target modules can be customized
- Supports various model architectures

### Training Process
1. Dataset validation and preprocessing
2. Model loading with LoRA configuration
3. Training with configurable parameters
4. Model saving and adapter extraction
5. Ollama model creation and registration

### Monitoring
- Real-time progress updates
- Loss tracking (training and validation)
- Epoch and step monitoring
- Error handling and recovery

## Troubleshooting

### Common Issues

1. **CUDA out of memory**
   - Reduce batch size
   - Increase gradient accumulation steps
   - Use a smaller model

2. **Training fails to start**
   - Check if Ollama is running
   - Verify dataset format
   - Check available disk space

3. **Model not appearing in Ollama**
   - Check training logs for errors
   - Verify model creation step
   - Try restarting Ollama

### Logs
Check the console output for detailed logs during training. The backend provides comprehensive logging for debugging issues.

## Performance Tips

1. **Use GPU** - Training is much faster with CUDA
2. **Optimize batch size** - Balance memory usage and speed
3. **Use appropriate LoRA rank** - Higher rank = more parameters but better performance
4. **Monitor GPU memory** - Use `nvidia-smi` to check usage

## Security Notes

- The API currently allows CORS from any origin (configure for production)
- No authentication is implemented (add for production use)
- File uploads are stored temporarily and cleaned up after training

## Development

To modify the training script or add features:

1. Edit `fine_tuning_script.py` for training logic
2. Edit `fine_tuning_api.py` for API endpoints
3. Update `requirements.txt` for dependencies
4. Test with the sample dataset in `sample_dataset.jsonl`
