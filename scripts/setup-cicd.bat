@echo off
REM Setup CI/CD Pipeline
REM Run this once to configure staging and production remotes

echo.
echo ========================================
echo   CI/CD Pipeline Setup
echo ========================================
echo.
echo This will configure:
echo   1. Git remotes for staging and production
echo   2. Hugging Face authentication
echo   3. Branch structure
echo.

set /p username="Enter your Hugging Face username: "
if "%username%"=="" (
    echo ERROR: Username required
    exit /b 1
)

echo.
echo ========================================
echo Step 1: Initialize Git Repository
echo ========================================
echo.

REM Check if git is initialized
if not exist .git (
    echo Initializing git repository...
    git init
    git add .
    git commit -m "Initial commit"
    echo ✓ Git repository initialized
) else (
    echo ✓ Git repository already initialized
)

echo.
echo ========================================
echo Step 2: Add Remote Repositories
echo ========================================
echo.

REM Add staging remote
git remote remove staging 2>nul
git remote add staging https://huggingface.co/spaces/%username%/video-transcriber-staging
echo ✓ Added staging remote

REM Add production remote
git remote remove production 2>nul
git remote add production https://huggingface.co/spaces/%username%/video-transcriber
echo ✓ Added production remote

echo.
echo Verifying remotes...
git remote -v

echo.
echo ========================================
echo Step 3: Create Branches
echo ========================================
echo.

REM Ensure we're on main branch
git branch -M main
echo ✓ Created main branch

echo.
echo ========================================
echo Step 4: Update Script Files
echo ========================================
echo.

REM Update deployment scripts with username
powershell -Command "(Get-Content scripts\deploy-staging.bat) -replace 'YOUR_USERNAME', '%username%' | Set-Content scripts\deploy-staging.bat"
powershell -Command "(Get-Content scripts\deploy-production.bat) -replace 'YOUR_USERNAME', '%username%' | Set-Content scripts\deploy-production.bat"
powershell -Command "(Get-Content scripts\deploy-both.bat) -replace 'YOUR_USERNAME', '%username%' | Set-Content scripts\deploy-both.bat"

echo ✓ Updated deployment scripts

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Your CI/CD pipeline is configured:
echo.
echo Staging:    https://huggingface.co/spaces/%username%/video-transcriber-staging
echo Production: https://huggingface.co/spaces/%username%/video-transcriber
echo.
echo ========================================
echo Next Steps:
echo ========================================
echo.
echo 1. Create TWO Spaces on Hugging Face:
echo    - video-transcriber-staging
echo    - video-transcriber
echo.
echo 2. Get your Hugging Face access token:
echo    https://huggingface.co/settings/tokens
echo.
echo 3. Test local code:
echo    python scripts\test_local.py
echo.
echo 4. Deploy to staging:
echo    scripts\deploy-staging.bat "Initial deployment"
echo.
echo 5. Test on staging, then deploy to production:
echo    scripts\deploy-production.bat
echo.
echo See CICD_SETUP.md for detailed documentation.
echo.
