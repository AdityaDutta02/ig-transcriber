@echo off
REM Deploy to Staging Space
REM Usage: deploy-staging.bat "Your commit message"

echo.
echo ========================================
echo   Deploying to STAGING
echo ========================================
echo.

IF "%~1"=="" (
    echo ERROR: Commit message required
    echo Usage: deploy-staging.bat "Your commit message"
    exit /b 1
)

echo Checking git status...
git status

echo.
echo Adding all changes...
git add .

echo.
echo Committing with message: %~1
git commit -m "%~1"

echo.
echo Pushing to staging Space...
git push staging main:main

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   ✓ Deployed to STAGING successfully!
    echo ========================================
    echo.
    echo View your staging app at:
    echo https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging
    echo.
    echo Watch build logs and test your changes.
    echo If tests pass, deploy to production with:
    echo   scripts\deploy-production.bat
    echo.
) ELSE (
    echo.
    echo ========================================
    echo   ✗ Deployment FAILED
    echo ========================================
    echo.
    echo Check the error messages above.
    echo.
)
