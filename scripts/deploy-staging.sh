#!/bin/bash
# Deploy to Staging Space
# Usage: ./scripts/deploy-staging.sh "Your commit message"

echo ""
echo "========================================"
echo "  Deploying to STAGING"
echo "========================================"
echo ""

if [ -z "$1" ]; then
    echo "ERROR: Commit message required"
    echo "Usage: ./scripts/deploy-staging.sh \"Your commit message\""
    exit 1
fi

echo "Checking git status..."
git status

echo ""
echo "Adding all changes..."
git add .

echo ""
echo "Committing with message: $1"
git commit -m "$1"

echo ""
echo "Pushing to staging Space..."
git push staging main:main

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "  ✓ Deployed to STAGING successfully!"
    echo "========================================"
    echo ""
    echo "View your staging app at:"
    echo "https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging"
    echo ""
    echo "Watch build logs and test your changes."
    echo "If tests pass, deploy to production with:"
    echo "  ./scripts/deploy-production.sh"
    echo ""
else
    echo ""
    echo "========================================"
    echo "  ✗ Deployment FAILED"
    echo "========================================"
    echo ""
    echo "Check the error messages above."
    echo ""
    exit 1
fi
