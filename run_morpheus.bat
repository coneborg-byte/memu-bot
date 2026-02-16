@echo off
title Morpheus Telegram Bot
echo Cleaning up existing Morpheus instances...
:: Taskkill will find any python process running morpheus_bot.py and end it
powershell -Command "Get-Process python | Where-Object {$_.CommandLine -like '*morpheus_bot.py*'} | Stop-Process -Force" 2>nul

:: Small delay to ensure memory is cleared
timeout /t 2 /nobreak >nul

echo Starting Morpheus (memU bot consolidated)...
"C:\Users\nvllm\AppData\Local\Programs\Python\Python312\python.exe" morpheus_bot.py
pause
