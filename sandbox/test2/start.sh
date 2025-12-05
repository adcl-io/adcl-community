#!/bin/bash
# Start all AI Red Team services

echo "================================================"
echo "Starting AI Red Team Services"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo -e "${YELLOW}Copying .env.example to .env...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please update .env with your API keys${NC}"
fi

# Start Redis via Docker Compose
echo -e "\n${BLUE}Starting Redis...${NC}"
docker compose up -d redis
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis started${NC}"
    sleep 2  # Give Redis time to initialize
else
    echo -e "${RED}✗ Failed to start Redis${NC}"
    exit 1
fi

# Check if Redis is responding
echo -e "\n${BLUE}Checking Redis connectivity...${NC}"
timeout 5 docker exec test2-redis-1 redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis is responding${NC}"
else
    echo -e "${RED}✗ Redis not responding${NC}"
    exit 1
fi

# Start API server
echo -e "\n${BLUE}Starting API server...${NC}"

# Check if already running
if pgrep -f "uvicorn api.main:app" > /dev/null; then
    echo -e "${YELLOW}⚠ API server already running${NC}"
    pkill -f "uvicorn api.main:app"
    sleep 1
fi

# Start in background
nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
API_PID=$!
sleep 3  # Give it time to start

# Check if API is responding
echo -e "\n${BLUE}Checking API server...${NC}"
curl -s http://localhost:8000/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ API server started (PID: $API_PID)${NC}"
    echo -e "${GREEN}✓ API available at http://localhost:8000${NC}"
    echo -e "${GREEN}✓ API docs at http://localhost:8000/docs${NC}"
else
    echo -e "${RED}✗ API server failed to start${NC}"
    echo -e "${YELLOW}Check api.log for errors${NC}"
    exit 1
fi

echo -e "\n================================================"
echo -e "${GREEN}All services started successfully${NC}"
echo "================================================"
echo -e "\n${BLUE}Service URLs:${NC}"
echo "  API Server:  http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo "  Redis:       localhost:6379"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  API:         tail -f api.log"
echo "  Redis:       docker logs -f test2-redis-1"
echo ""
echo -e "${BLUE}Management:${NC}"
echo "  Status:      ./status.sh"
echo "  Stop:        ./stop.sh"
echo "  Bounce:      ./bounce.sh"
