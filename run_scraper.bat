@echo off
echo Running Peace Event Scraper...
cd /d "%~dp0"
py -3.12 simple_peace_scraper.py
echo.
echo Press any key to exit...
pause > nul
