#!/bin/bash

# HackerCast RSS Server Startup Script

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting HackerCast RSS Server...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Please run 'python -m venv venv' first.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
if ! python -c "import flask, feedgen, mutagen" 2>/dev/null; then
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install flask feedgen mutagen
fi

# Ensure output/audio directory exists
mkdir -p output/audio

# Start the server
echo -e "${GREEN}RSS Server starting on http://localhost:8080${NC}"
echo -e "${GREEN}RSS Feed available at: http://localhost:8080/rss${NC}"
echo -e "${GREEN}Latest episode info: http://localhost:8080/latest${NC}"
echo -e "${GREEN}Health check: http://localhost:8080/health${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python rss_server.py