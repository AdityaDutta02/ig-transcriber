@echo off
REM Deploy to Production Space
REM Usage: deploy-production.bat

echo.
echo ========================================
echo   Deploying to PRODUCTION
echo ========================================
echo.
echo WARNING: This will update your live app!
echo Make sure you tested in staging first.
echo.

set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" (
    echo Deployment cancelled.
    exit /b 0
)

echo.
echo Pushing current code to production Space...
git push production main:main

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   ✓ Deployed to PRODUCTION successfully!
    echo ========================================
    echo.
    echo Your production app is updating at:
    echo https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber
    echo.
    echo Build takes 5-10 minutes. Old version runs until new version is ready.
    echo NO DOWNTIME - users can keep using the app during build.
    echo.
    echo Monitor deployment:
    echo 1. Go to your production Space
    echo 2. Click "Logs" tab
    echo 3. Wait for build to complete
    echo 4. Test the updated app
    echo.
) ELSE (
    echo.
    echo ========================================
    echo   ✗ Deployment FAILED
    echo ========================================
    echo.
    echo Check the error messages above.
    echo Don't worry - your old production version is still running!
    echo.
)
