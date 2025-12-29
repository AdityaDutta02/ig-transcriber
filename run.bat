@echo off
REM Run Video Transcriber with automatic venv activation

cd /d "%~dp0"

echo.
echo ========================================
echo   Video Transcriber - Local Network
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please create it first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Checking Streamlit installation...
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Streamlit not installed in venv!
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Installation failed. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo.
echo Getting local IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do set IP=%%a
set IP=%IP: =%

echo.
echo ========================================
echo   Starting Server
echo ========================================
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

REM Start Streamlit
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
