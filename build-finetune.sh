#!/bin/bash
# Build script for Fine-tuning Docker Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
USE_CUDA=false
CUDA_VER="cu121"
BUILD_ARGS=""
PUSH=false
TAG="latest"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and optionally push the fine-tuning Docker image.

OPTIONS:
    -c, --cuda              Enable CUDA support
    -v, --cuda-version      CUDA version (default: cu121)
    -t, --tag               Image tag (default: latest)
    -p, --push              Push image to registry after building
    -r, --registry          Registry URL (default: local)
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Build CPU-only image
    $0 -c                                # Build with CUDA support
    $0 -c -v cu118                       # Build with CUDA 11.8
    $0 -c -t v1.0.0 -p                  # Build, tag, and push
    $0 -c -r myregistry.com -t v1.0.0   # Build for specific registry

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--cuda)
            USE_CUDA=true
            shift
            ;;
        -v|--cuda-version)
            CUDA_VER="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set image name
if [[ -n "$REGISTRY" ]]; then
    IMAGE_NAME="${REGISTRY}/finetune-backend:${TAG}"
else
    IMAGE_NAME="finetune-backend:${TAG}"
fi

print_info "Building fine-tuning Docker image..."
print_info "Image name: $IMAGE_NAME"
print_info "CUDA enabled: $USE_CUDA"
if [[ "$USE_CUDA" == "true" ]]; then
    print_info "CUDA version: $CUDA_VER"
fi

# Check if Dockerfile exists
if [[ ! -f "Dockerfile.finetune" ]]; then
    print_error "Dockerfile.finetune not found in current directory"
    exit 1
fi

# Check if backend directory exists
if [[ ! -d "backend" ]]; then
    print_error "backend directory not found in current directory"
    exit 1
fi

# Build the image
print_info "Starting Docker build..."

BUILD_CMD="docker build -f Dockerfile.finetune"
BUILD_CMD="$BUILD_CMD --build-arg USE_CUDA=$USE_CUDA"
BUILD_CMD="$BUILD_CMD --build-arg USE_CUDA_VER=$CUDA_VER"
BUILD_CMD="$BUILD_CMD --build-arg UID=$(id -u)"
BUILD_CMD="$BUILD_CMD --build-arg GID=$(id -g)"
BUILD_CMD="$BUILD_CMD -t $IMAGE_NAME ."

print_info "Build command: $BUILD_CMD"

if eval $BUILD_CMD; then
    print_success "Docker image built successfully: $IMAGE_NAME"
else
    print_error "Docker build failed"
    exit 1
fi

# Push image if requested
if [[ "$PUSH" == "true" ]]; then
    print_info "Pushing image to registry..."
    if docker push "$IMAGE_NAME"; then
        print_success "Image pushed successfully: $IMAGE_NAME"
    else
        print_error "Failed to push image"
        exit 1
    fi
fi

# Show next steps
print_info "Next steps:"
echo "1. Copy environment template:"
echo "   cp env.finetune.example .env.finetune"
echo ""
echo "2. Edit configuration:"
echo "   nano .env.finetune"
echo ""
echo "3. Start the service:"
echo "   docker-compose -f docker-compose.finetune.yaml up -d"
echo ""
echo "4. Check logs:"
echo "   docker-compose -f docker-compose.finetune.yaml logs -f finetune-backend"
echo ""
echo "5. Access the API:"
echo "   http://localhost:8001"

print_success "Build completed successfully!"
