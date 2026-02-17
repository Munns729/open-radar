@echo off
echo Starting Investor Radar - Visual Mode...

:: 1. Start Web Server in background (hidden/minimized if possible, but start new window is easiest)
start "Investor Radar Dashboard Server" python -m http.server 8000 --directory src/web

:: 2. Wait a moment for server to spin up
timeout /t 2 /nobreak >nul

:: 3. Open Dashboard in Browser
start http://localhost:8000/dashboard.html

:: 4. Run the Scanner in this window
echo.
echo ========================================================
echo  SCANNER RUNNING... CHECK BROWSER FOR VISUALIZATION
echo ========================================================
echo.
:: Use -u (unbuffered) and -m (module) for best results
python -u -m src.universe.workflow --mode full --countries FR

:: 5. Pause so window doesn't close immediately on error
pause
