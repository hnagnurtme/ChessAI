#!/bin/bash

##############################################
# Local Test Script - Build and Test Images
##############################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load .env if exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if DOCKERHUB_USERNAME is set
if [ -z "$DOCKERHUB_USERNAME" ]; then
    log_error "DOCKERHUB_USERNAME not set. Please set it in .env file or export it."
    exit 1
fi

log_info "Building Docker images locally..."

# Build backend
log_info "Building backend image..."
docker build -t $DOCKERHUB_USERNAME/chess-bot-backend:latest ./Backend

# Build frontend
log_info "Building frontend image..."
docker build -t $DOCKERHUB_USERNAME/chess-bot-frontend:latest ./Frontend

log_info "✅ Build complete!"

# Ask if user wants to push
read -p "Do you want to push images to Docker Hub? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Logging in to Docker Hub..."
    docker login
    
    log_info "Pushing backend image..."
    docker push $DOCKERHUB_USERNAME/chess-bot-backend:latest
    
    log_info "Pushing frontend image..."
    docker push $DOCKERHUB_USERNAME/chess-bot-frontend:latest
    
    log_info "✅ Push complete!"
fi

# Ask if user wants to test locally
read -p "Do you want to start containers locally? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting containers with docker-compose..."
    docker-compose up -d
    
    log_info "Waiting for services to start..."
    sleep 10
    
    log_info "Container status:"
    docker ps --filter "name=chess-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    log_info "Testing services..."
    
    # Test backend
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_info "✅ Backend is healthy!"
    else
        log_warn "⚠️ Backend health check failed"
    fi
    
    # Test frontend
    if curl -f http://localhost:5175 &> /dev/null; then
        log_info "✅ Frontend is healthy!"
    else
        log_warn "⚠️ Frontend health check failed"
    fi
    
    log_info "Services available at:"
    echo "  - Backend: http://localhost:8000/docs"
    echo "  - Frontend: http://localhost:5175"
    echo ""
    log_info "To view logs: docker-compose logs -f"
    log_info "To stop: docker-compose down"
fi

log_info "🎉 Done!"
