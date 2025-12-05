#!/bin/bash
# Stop all AI Red Team services

echo "================================================"
echo "Stopping AI Red Team Services"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop API server (if running as background process)
echo -e "\n${YELLOW}Stopping API server...${NC}"
pkill -f "uvicorn api.main:app" && echo -e "${GREEN}✓ API server stopped${NC}" || echo -e "${YELLOW}⊘ API server not running${NC}"

# Stop Redis container
echo -e "\n${YELLOW}Stopping Redis container...${NC}"
docker compose stop redis 2>/dev/null && echo -e "${GREEN}✓ Redis stopped${NC}" || echo -e "${YELLOW}⊘ Redis not running${NC}"

# Stop all Docker Compose services
echo -e "\n${YELLOW}Stopping all Docker Compose services...${NC}"
docker compose down 2>/dev/null && echo -e "${GREEN}✓ Docker Compose services stopped${NC}" || echo -e "${YELLOW}⊘ No Docker Compose services running${NC}"

echo -e "\n================================================"
echo -e "${GREEN}Services stopped${NC}"
echo "================================================"
