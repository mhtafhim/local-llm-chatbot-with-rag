@echo off
echo Installing requirements (first run only)...
pip install -r requirements.txt

echo.
echo Starting RAG backend on http://0.0.0.0:8001
echo Anyone on your network can reach it via http://YOUR_IP:8001
echo.
uvicorn main:app --host 0.0.0.0 --port 8001
pause
