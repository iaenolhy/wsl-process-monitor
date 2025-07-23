@echo off
echo WSL Process Monitor - Backend Launcher
echo ========================================

echo.
echo Starting backend server...
echo Server URL: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop the server
echo ========================================

cd backend
set PYTHONUNBUFFERED=1
python -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --log-level info

echo.
echo Backend server stopped
pause
