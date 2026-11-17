@echo off
rem Double-click this file to start Ash's island.
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed. Get the LTS version from https://nodejs.org and run this again.
  pause
  exit /b 1
)
if not exist node_modules (
  echo Installing, this takes a minute the first time...
  call npm install
)
if not exist .env copy .env.example .env >nul
call npm start
pause
