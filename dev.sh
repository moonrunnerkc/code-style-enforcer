#!/bin/bash
# Author: Bradley R. Kinnard — start everything in one terminal

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Code Style Enforcer Dev Environment ===${NC}"

# Check dependencies
command -v redis-cli >/dev/null 2>&1 || { echo -e "${RED}redis-cli not found. Install redis.${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || { echo -e "${RED}python not found.${NC}"; exit 1; }

# Kill any existing processes on our ports
echo -e "${YELLOW}Cleaning up old processes...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
pkill -f "feedback_processor" 2>/dev/null || true
sleep 1

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start Redis if not running
if ! redis-cli ping >/dev/null 2>&1; then
    echo -e "${YELLOW}Starting Redis...${NC}"
    redis-server --daemonize yes
    sleep 1
fi
echo -e "${GREEN}✓ Redis running${NC}"

# Export env vars for local dev (no LocalStack needed)
export REDIS_URL="redis://localhost:6379"
export USE_LOCAL_SQS="true"
export USE_LOCAL_DYNAMO="true"

cd "$(dirname "$0")"

# Start backend
echo -e "${YELLOW}Starting backend on :8000...${NC}"
poetry run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 2

# Start feedback worker
echo -e "${YELLOW}Starting feedback worker...${NC}"
poetry run python -m src.backend.workers.feedback_processor &
WORKER_PID=$!

# Start frontend
echo -e "${YELLOW}Starting frontend on :3000...${NC}"
cd frontend && npm run dev -- --port 3000 &
FRONTEND_PID=$!
cd ..

echo -e "\n${GREEN}=== All services running ===${NC}"
echo -e "  Backend:  http://localhost:8000"
echo -e "  Frontend: http://localhost:3000"
echo -e "  Redis:    localhost:6379"
echo -e "  Worker:   Running (memory mode)"
echo -e "\nPress Ctrl+C to stop all services\n"

# Wait for any process to exit
wait
