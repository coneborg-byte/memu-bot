@echo off
title Morpheus Control - DNS
echo.
echo ========================================================
echo     MORPHEUS (OpenClaw) Control Loop
echo ========================================================
echo.

echo [1/2] Waking up OpenClaw Docker...
docker start openclaw >nul 2>&1

echo [2/2] Starting local Mission Control...
start "Mission Control" /min "C:\Users\nvllm\AppData\Local\Programs\Python\Python312\python.exe" mission_control.py

echo.
echo Morpheus is now online. 🦾
echo This window will close in 5 seconds...
timeout /t 5 >nul
exit

