@echo off
REM Deploy to Staging, then Production
REM Usage: deploy-both.bat "Your commit message"

echo.
echo ========================================
echo   Full Deployment Pipeline
echo ========================================
echo   1. Deploy to Staging
echo   2. You test on staging
echo   3. Deploy to Production
echo ========================================
echo.

IF "%~1"=="" (
    echo ERROR: Commit message required
    echo Usage: deploy-both.bat "Your commit message"
    exit /b 1
)

REM Step 1: Deploy to staging
echo.
echo STEP 1: Deploying to STAGING...
echo ========================================
echo.

git add .
git commit -m "%~1"
git push staging main:main

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ✗ Staging deployment failed. Stopping here.
    exit /b 1
)

echo.
echo ✓ Staging deployment complete!
echo.
echo ========================================
echo STEP 2: TEST YOUR CHANGES
echo ========================================
echo.
echo Visit your staging app:
echo https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging
echo.
echo Test thoroughly:
echo   - Single URL processing
echo   - CSV batch processing
echo   - Caption generation
echo   - File downloads
echo.
echo.

set /p proceed="Tests passed? Deploy to PRODUCTION? (y/n): "
if /i not "%proceed%"=="y" (
    echo.
    echo Deployment stopped. Fix issues and try again.
    exit /b 0
)

REM Step 3: Deploy to production
echo.
echo STEP 3: Deploying to PRODUCTION...
echo ========================================
echo.

git push production main:main

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   ✓ FULL DEPLOYMENT COMPLETE!
    echo ========================================
    echo.
    echo ✓ Staging: Updated and tested
    echo ✓ Production: Deploying now (no downtime)
    echo.
    echo Your production app is updating at:
    echo https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber
    echo.
    echo Monitor build in Logs tab. Old version runs until new version ready.
    echo.
) ELSE (
    echo.
    echo ✗ Production deployment failed.
    echo Check the error messages above.
    echo Don't worry - production is still running the old version!
    echo.
)
