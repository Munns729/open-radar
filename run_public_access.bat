@echo off
echo Starting Investor Radar - Public Access Mode (ngrok)...
echo.
echo [INFO] This will create a public URL for your dashboard.
echo.

:: Run the python wrapper which handles ngrok + uvicorn
python scripts/canonical/run_public.py

pause
