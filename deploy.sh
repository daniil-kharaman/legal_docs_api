#!/bin/bash
set -e

echo "🚀 Starting deployment..."

# Use production compose file
COMPOSE_FILE="docker-compose.prod.yml"

# Login to Docker Hub (for private repositories)
echo "🔐 Logging in to Docker Hub..."
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Pull latest images from Docker Hub
echo "📥 Pulling Docker images..."
docker compose -f $COMPOSE_FILE pull

# Stop and remove old containers
echo "🛑 Stopping old containers..."
docker compose -f $COMPOSE_FILE down

# Start new containers in detached mode
echo "▶️  Starting new containers..."
docker compose -f $COMPOSE_FILE up -d

# Show running containers
echo "✅ Deployment complete! Running containers:"
docker compose -f $COMPOSE_FILE ps

# Show logs from last 50 lines
echo ""
echo "📋 Recent logs:"
docker compose -f $COMPOSE_FILE logs --tail=50

echo ""
echo "🎉 Deployment successful!"
echo "API should be accessible at: http://$(curl -s http://checkip.amazonaws.com)"