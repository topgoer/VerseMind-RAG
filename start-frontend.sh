#!/bin/bash
# filepath: d:\Github\VerseMind-RAG\start-frontend.sh

# Change directory to frontend
cd frontend

# Parse command line arguments
MODE="prod"
if [ "$1" == "dev" ]; then
    MODE="dev"
fi

if [ "$MODE" == "dev" ]; then
    echo "Starting development server..."
    npm run dev
else
    # Clean the dist directory to remove old build files
    if [ -d "dist" ]; then
        echo "Removing old build files..."
        rm -rf dist
    fi
    
    # Build a fresh production version
    echo "Building new production version..."
    npm run build
    
    # Preview the newly built production version
    echo "Starting preview server..."
    npm run preview
fi

cd ..
echo ""
echo "To run in development mode: ./start-frontend.sh dev"
echo "To run in production preview mode: ./start-frontend.sh"
