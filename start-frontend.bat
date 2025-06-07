@echo off
REM filepath: d:\Github\VerseMind-RAG\start-frontend.bat
cd frontend

REM Parse command line arguments
set MODE=prod
if "%1"=="dev" set MODE=dev

if "%MODE%"=="dev" (
    echo Starting development server...
    npm run dev
) else (
    REM Clean the dist directory to remove old build files
    if exist "dist" (
        echo Removing old build files...
        rmdir /s /q dist
    )
    
    REM Build a fresh production version
    echo Building new production version...

    REM Build the frontend
    call npm run build > NUL
    
    REM Preview the newly built production version
    echo Starting preview server...
    call npm run preview
)

cd ..
echo.
echo To run in development mode: start-frontend.bat dev
echo To run in production preview mode: start-frontend.bat
@echo on