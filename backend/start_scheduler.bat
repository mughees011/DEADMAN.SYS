@echo off
cd /d "C:\Users\Mughees Siddiqui\Desktop\DEADMAN.SYS\backend"
call .\venv\Scripts\activate.bat
echo [%date% %time%] Starting DEADMAN.SYS Scheduler >> scheduler.log
python main.py >> scheduler.log 2>&1
