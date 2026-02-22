@echo off
REM RADAR Pipeline - overnight mode (6h discovery + enrichment, then score + tier + brief)
REM Usage: run from project dir, or: scripts\canonical\run_autonomous.bat

cd /d "%~dp0..\.."
python scripts/canonical/run_daily_pipeline.py --duration 6 %*
exit /b %ERRORLEVEL%
