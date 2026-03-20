#!/bin/bash
set -e

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== diaMCP Installer ===${NC}\n"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker compose is available (standalone or plugin)
if ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

# Determine if already installed
if [ -d ".git" ] && [ -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}diaMCP installation detected.${NC}"
    echo "Updating to latest version..."
    
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null
    
    echo -e "\n${GREEN}Rebuilding and restarting...${NC}"
    docker compose up --build -d
    
    echo -e "\n${GREEN}=== diaMCP Updated! ===${NC}"
    echo "Container restarted with latest changes."
    echo "Access the MCP at: http://localhost:8000/mcp"
else
    echo -e "${YELLOW}No existing installation found. Setting up fresh install...${NC}"
    
    REPO_URL="https://github.com/chartrambiz/diaMCP.git"
    TARGET_DIR="diaMCP"
    
    if [ -d "$TARGET_DIR" ]; then
        echo -e "${RED}Error: Directory '$TARGET_DIR' already exists.${NC}"
        echo "Remove it or clone to a different location."
        exit 1
    fi
    
    echo -e "\nCloning repository..."
    git clone "$REPO_URL" "$TARGET_DIR"
    
    cd "$TARGET_DIR"
    
    echo -e "\n${GREEN}Building and starting container...${NC}"
    docker compose up --build -d
    
    echo -e "\n${GREEN}=== diaMCP Installed! ===${NC}"
    echo "Container is now running."
    echo ""
    echo "Next steps:"
    echo "1. Start llama-server with MCP proxy:"
    echo "   llama-server --webui-mcp-proxy -m model.gguf -c 32768 --host 0.0.0.0 --port 8080"
    echo ""
    echo "2. In the webui, go to MCP Settings:"
    echo "   - Toggle 'Enable llama-server proxy' ON"
    echo "   - Add MCP URL: http://localhost:8000/mcp"
    echo ""
    echo "3. After modifying tools, run: ./restart.sh"
    echo ""
    echo "Access the MCP at: http://localhost:8000/mcp"
fi
