@echo off
REM filepath: d:\Github\VerseMind-RAG\start-backend.bat

REM Activate conda environment
call conda activate versemind-rag || (
  echo Error: Failed to activate conda environment versemind-rag
  echo Please make sure you have created the conda environment:
  echo conda create -n versemind-rag python=3.12.9
  pause
  exit /b 1
)

REM Change directory to backend
cd backend

REM Start the FastAPI server
echo Starting backend server...
uvicorn app.main:app --host 0.0.0.0 --port 8200 --reload

@echo on