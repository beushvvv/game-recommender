@echo off
cd /d D:\game_app
call venv\Scripts\activate

start /b python app.py

echo Waiting for server to start...
ping -n 3 127.0.0.1 >nul

start http://127.0.0.1:5001

echo Server is running. Press any key to stop...
pause >nul
taskkill /f /im python.exe