#!/bin/bash
# Bounce (restart) all AI Red Team services

echo "================================================"
echo "Bouncing AI Red Team Services"
echo "================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Stop services
echo -e "\n${BLUE}Step 1: Stopping services...${NC}"
./stop.sh

# Wait a moment
echo -e "\n${BLUE}Waiting 2 seconds...${NC}"
sleep 2

# Start services
echo -e "\n${BLUE}Step 2: Starting services...${NC}"
./start.sh

# Check status
echo -e "\n${BLUE}Step 3: Verifying services...${NC}"
sleep 2
./status.sh

# Run Phase 1 tests
echo -e "\n${BLUE}Step 4: Running Phase 1 tests...${NC}"
echo ""
python3 test_phase1.py

echo -e "\n================================================"
echo -e "${GREEN}Bounce complete!${NC}"
echo "================================================"
