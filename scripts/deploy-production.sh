#!/bin/bash
# Deploy to Production Space
# Usage: ./scripts/deploy-production.sh

echo ""
echo "========================================"
echo "  Deploying to PRODUCTION"
echo "========================================"
echo ""
echo "WARNING: This will update your live app!"
echo "Make sure you tested in staging first."
echo ""

read -p "Continue? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Pushing current code to production Space..."
git push production main:main

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  ✓ Deployed to PRODUCTION successfully!"
    echo "========================================"
    echo ""
    echo "Your production app is updating at:"
    echo "https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber"
    echo ""
    echo "Build takes 5-10 minutes. Old version runs until new version is ready."
    echo "NO DOWNTIME - users can keep using the app during build."
    echo ""
    echo "Monitor deployment:"
    echo "1. Go to your production Space"
    echo "2. Click 'Logs' tab"
    echo "3. Wait for build to complete"
    echo "4. Test the updated app"
    echo ""
else
    echo ""
    echo "========================================"
    echo "  ✗ Deployment FAILED"
    echo "========================================"
    echo ""
    echo "Check the error messages above."
    echo "Don't worry - your old production version is still running!"
    echo ""
    exit 1
fi
