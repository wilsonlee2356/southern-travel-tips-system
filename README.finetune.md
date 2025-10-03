# Fine-tuning Docker Setup

This directory contains Docker configuration for the LoRA fine-tuning backend service.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM (16GB+ recommended)
- GPU with CUDA support (optional but recommended for faster training)

### 2. Configuration

Copy the environment template and customize it:

```bash
cp env.finetune.example .env.finetune
# Edit .env.finetune with your settings
```

### 3. Build and Run

```bash
# Build the fine-tuning service
docker-compose -f docker-compose.finetune.yaml build

# Start the services
docker-compose -f docker-compose.finetune.yaml up -d

# View logs
docker-compose -f docker-compose.finetune.yaml logs -f finetune-backend
```

### 4. Access the Service

- **Fine-tuning API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## Services Included

### Core Services

- **finetune-backend**: Main fine-tuning API service
- **ollama**: Model inference service (optional)
- **redis**: Caching and session management (optional)

### Monitoring Services (Optional)

- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboard

## Configuration

### Environment Variables

Key configuration options in `.env.finetune`:

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_CUDA` | Enable GPU support | `false` |
| `USE_CUDA_VER` | CUDA version | `cu121` |
| `MEMORY_LIMIT` | Container memory limit | `16G` |
| `CPU_LIMIT` | Container CPU limit | `8.0` |
| `FINETUNE_LOG_LEVEL` | Logging level | `INFO` |

### GPU Support

To enable GPU support:

1. Install NVIDIA Docker runtime
2. Set `USE_CUDA=true` in `.env.finetune`
3. Uncomment GPU configuration in `docker-compose.finetune.yaml`

### Resource Requirements

| Model Size | RAM | GPU VRAM | Training Time |
|------------|-----|----------|---------------|
| 3B | 8GB | 4GB | 30-60 min |
| 7B | 16GB | 8GB | 1-2 hours |
| 14B | 32GB | 16GB | 2-4 hours |
| 32B | 64GB | 24GB+ | 4-8 hours |

## Usage

### API Endpoints

#### Start Training
```bash
curl -X POST "http://localhost:8001/api/fine-tuning/start" \
  -F "file=@dataset.jsonl" \
  -F "base_model=qwen2.5:7b" \
  -F "adapter_name=my-adapter"
```

#### Check Training Status
```bash
curl "http://localhost:8001/api/fine-tuning/status/{session_id}"
```

#### List Training Sessions
```bash
curl "http://localhost:8001/api/fine-tuning/sessions"
```

### Dataset Format

The API expects datasets in JSONL format:

```jsonl
{"prompt": "機票資料: ANA全日空航空，香港到東京羽田，HK$2,390", "response": "{\"Destination\": \"東京\", \"Header\": \"精選東京遊！HK$2,390即刻出發！\"}"}
{"prompt": "機票資料: 國泰航空，香港到悉尼，HK$3,500", "response": "{\"Destination\": \"悉尼\", \"Header\": \"澳洲之旅！HK$3,500起飛！\"}"}
```

## Monitoring

### Health Checks

The service includes built-in health checks:

```bash
# Check service health
curl http://localhost:8001/health

# Check container health
docker ps
```

### Logs

View logs for different services:

```bash
# Fine-tuning backend logs
docker-compose -f docker-compose.finetune.yaml logs finetune-backend

# All services logs
docker-compose -f docker-compose.finetune.yaml logs

# Follow logs in real-time
docker-compose -f docker-compose.finetune.yaml logs -f
```

### Metrics (Optional)

If monitoring services are enabled:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Troubleshooting

### Common Issues

1. **Out of Memory**
   - Reduce `MEMORY_LIMIT` or use smaller models
   - Enable gradient checkpointing in training config

2. **CUDA Errors**
   - Verify NVIDIA Docker runtime is installed
   - Check CUDA version compatibility
   - Ensure GPU is available: `nvidia-smi`

3. **Training Fails**
   - Check dataset format and size
   - Verify model availability
   - Review logs for specific errors

4. **Slow Training**
   - Enable GPU support
   - Increase batch size (if memory allows)
   - Use gradient accumulation

### Debug Mode

Enable debug logging:

```bash
# In .env.finetune
FINETUNE_LOG_LEVEL=DEBUG
```

### Container Shell Access

```bash
# Access running container
docker exec -it finetune-backend bash

# Run new container for debugging
docker run -it --rm finetune-backend bash
```

## Development

### Building from Source

```bash
# Build with specific CUDA version
docker build -f Dockerfile.finetune \
  --build-arg USE_CUDA=true \
  --build-arg USE_CUDA_VER=cu121 \
  -t finetune-backend:latest .
```

### Custom Dependencies

To add custom Python packages:

1. Create `requirements-custom.txt`
2. Modify `Dockerfile.finetune` to install it
3. Rebuild the image

### Local Development

For local development without Docker:

```bash
cd backend
pip install -r requirements.txt
python fine_tuning_api.py
```

## Security

### Best Practices

1. **Change default passwords** in production
2. **Use secrets management** for sensitive data
3. **Enable HTTPS** for production deployments
4. **Restrict network access** to necessary ports only
5. **Regular security updates** of base images

### Network Security

The default configuration exposes:
- Port 8001: Fine-tuning API
- Port 11434: Ollama (if enabled)
- Port 3000: Grafana (if enabled)
- Port 9090: Prometheus (if enabled)

## Support

For issues and questions:

1. Check the logs first
2. Review this documentation
3. Check the main project repository
4. Create an issue with detailed information

## License

This Docker setup follows the same license as the main project.
