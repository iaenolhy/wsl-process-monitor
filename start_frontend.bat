@echo off
echo WSL Process Monitor - Frontend Launcher
echo ========================================

echo.
echo Checking Node.js environment...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found
    echo Please install Node.js from https://nodejs.org
    echo.
    pause
    exit /b 1
)

npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm not found
    echo Please install Node.js from https://nodejs.org
    echo.
    pause
    exit /b 1
)

echo Node.js environment OK

echo.
echo Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    npm install
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        echo.
        pause
        exit /b 1
    )
    cd ..
)

echo Dependencies OK

echo.
echo Starting frontend development server...
echo Server will be available at: http://localhost:5173
echo Press Ctrl+C to stop the server
echo ========================================

cd frontend
npm run dev

echo.
echo Frontend server stopped
pause
