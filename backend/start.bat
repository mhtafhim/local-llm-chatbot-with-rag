@echo off
setlocal enabledelayedexpansion

echo Installing requirements (first run only)...
pip install -r requirements.txt

if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" set "%%A=%%B"
  )
)

echo.
echo Starting RAG backend on http://0.0.0.0:8001
echo Anyone on your network can reach it via http://YOUR_IP:8001
echo Provider: %LLM_PROVIDER%
echo.
uvicorn main:app --host 0.0.0.0 --port 8001
pause
