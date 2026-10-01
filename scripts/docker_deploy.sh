#!/bin/bash
# Rebuilds and redeploys the public site container: removes any existing
# steep-seeker container, builds a fresh image from the current checkout
# (data/db.db and static/maps, static/thumbnails must already be synced in --
# see Dockerfile), runs it, and smoke-tests it.
#
# Run from the repo root:
#
#     ./scripts/docker_deploy.sh

set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE_NAME="steep-seeker"
TAG="${1:-latest}"
CONTAINER_NAME="steep-seeker"
PORT="8000"

echo "==> Removing existing container (if any)"
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "==> Building $IMAGE_NAME:$TAG"
docker build -t "$IMAGE_NAME:$TAG" .

echo "==> Starting $CONTAINER_NAME"
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "127.0.0.1:$PORT:$PORT" \
    --restart unless-stopped \
    "$IMAGE_NAME:$TAG"

echo "==> Pruning dangling images left over from previous builds"
docker image prune -f >/dev/null

echo "==> Waiting for container to come up"
for _ in $(seq 1 15); do
    if curl -fs "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
        echo "==> OK: site responded on port $PORT"
        exit 0
    fi
    sleep 1
done

echo "==> Site did not respond in time, recent logs:"
docker logs --tail 50 "$CONTAINER_NAME"
exit 1
