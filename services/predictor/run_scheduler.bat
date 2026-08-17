@echo off
chcp 65001 >nul
REM Launched manually or by Windows Task Scheduler to run scheduler.py forever.
REM scheduler.py itself logs to BOTH this console window and logs\scheduler.log (UTF-8),
REM so this window shows the live activity while the file keeps the history.
cd /d C:\ziegoProject\kos\services\predictor
"C:\ziegoProject\kos\services\predictor\.venv\Scripts\python.exe" scheduler.py
echo.
echo [scheduler.py exited - see logs\scheduler.log for details]
pause
