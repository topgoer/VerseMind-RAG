#!/bin/bash
# filepath: d:\Github\VerseMind-RAG\start-backend.sh

# Activate conda environment (if using conda)
if command -v conda &> /dev/null; then
    # Conda is available
    echo "Activating conda environment..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate versemind-rag || {
        echo "Error: Failed to activate conda environment versemind-rag"
        echo "Please make sure you have created the conda environment:"
        echo "conda create -n versemind-rag python=3.12.9"
        exit 1
    }
else
    # Conda not available, try virtual environment 
    if [ -d "venv" ] || [ -d ".venv" ]; then
        echo "Activating virtual environment..."
        if [ -d "venv" ]; then
            source venv/bin/activate
        else
            source .venv/bin/activate
        fi
    fi
fi

# Change directory to backend
cd backend

# Start the FastAPI server
echo "Starting backend server..."
uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload --no-access-log
