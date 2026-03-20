#!/bin/bash
set -e

echo "Rebuilding diaMCP container..."
docker compose build

echo "Restarting container..."
docker compose up -d

echo "Waiting for container to be healthy..."
sleep 2

if docker compose ps | grep -q "Up"; then
    echo "diaMCP is running!"
else
    echo "ERROR: Container failed to start"
    exit 1
fi
