@echo off
REM Start Video Transcriber on Local Network
REM All devices on your network can access the app

echo.
echo ========================================
echo   Video Transcriber - Local Network
echo ========================================
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do set IP=%%a
set IP=%IP: =%

echo Starting Streamlit on local network...
echo.
echo Your app will be accessible at:
echo.
echo   On this computer:
echo   http://localhost:8501
echo.
echo   From other devices on your network:
echo   http://%IP%:8501
echo.
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Streamlit with network access
streamlit run app.py --server.address 0.0.0.0 --server.port 8501

pause
