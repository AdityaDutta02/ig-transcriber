#!/bin/bash
# Setup CI/CD Pipeline
# Run this once to configure staging and production remotes

echo ""
echo "========================================"
echo "  CI/CD Pipeline Setup"
echo "========================================"
echo ""
echo "This will configure:"
echo "  1. Git remotes for staging and production"
echo "  2. Hugging Face authentication"
echo "  3. Branch structure"
echo ""

read -p "Enter your Hugging Face username: " username
if [ -z "$username" ]; then
    echo "ERROR: Username required"
    exit 1
fi

echo ""
echo "========================================"
echo "Step 1: Initialize Git Repository"
echo "========================================"
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit"
    echo "✓ Git repository initialized"
else
    echo "✓ Git repository already initialized"
fi

echo ""
echo "========================================"
echo "Step 2: Add Remote Repositories"
echo "========================================"
echo ""

# Add staging remote
git remote remove staging 2>/dev/null
git remote add staging https://huggingface.co/spaces/$username/video-transcriber-staging
echo "✓ Added staging remote"

# Add production remote
git remote remove production 2>/dev/null
git remote add production https://huggingface.co/spaces/$username/video-transcriber
echo "✓ Added production remote"

echo ""
echo "Verifying remotes..."
git remote -v

echo ""
echo "========================================"
echo "Step 3: Create Branches"
echo "========================================"
echo ""

# Ensure we're on main branch
git branch -M main
echo "✓ Created main branch"

echo ""
echo "========================================"
echo "Step 4: Update Script Files"
echo "========================================"
echo ""

# Update deployment scripts with username
sed -i.bak "s/YOUR_USERNAME/$username/g" scripts/deploy-staging.sh
sed -i.bak "s/YOUR_USERNAME/$username/g" scripts/deploy-production.sh
sed -i.bak "s/YOUR_USERNAME/$username/g" scripts/deploy-staging.bat
sed -i.bak "s/YOUR_USERNAME/$username/g" scripts/deploy-production.bat
sed -i.bak "s/YOUR_USERNAME/$username/g" scripts/deploy-both.bat

# Make scripts executable
chmod +x scripts/*.sh

echo "✓ Updated deployment scripts"

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Your CI/CD pipeline is configured:"
echo ""
echo "Staging:    https://huggingface.co/spaces/$username/video-transcriber-staging"
echo "Production: https://huggingface.co/spaces/$username/video-transcriber"
echo ""
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo ""
echo "1. Create TWO Spaces on Hugging Face:"
echo "   - video-transcriber-staging"
echo "   - video-transcriber"
echo ""
echo "2. Get your Hugging Face access token:"
echo "   https://huggingface.co/settings/tokens"
echo ""
echo "3. Test local code:"
echo "   python scripts/test_local.py"
echo ""
echo "4. Deploy to staging:"
echo "   ./scripts/deploy-staging.sh \"Initial deployment\""
echo ""
echo "5. Test on staging, then deploy to production:"
echo "   ./scripts/deploy-production.sh"
echo ""
echo "See CICD_SETUP.md for detailed documentation."
echo ""
