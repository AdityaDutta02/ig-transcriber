# Deployment Scripts

Automated scripts for zero-downtime CI/CD deployment to Hugging Face Spaces.

## Setup (One-time)

Run this first to configure your CI/CD pipeline:

### Windows:
```cmd
scripts\setup-cicd.bat
```

### Mac/Linux/WSL:
```bash
chmod +x scripts/*.sh
./scripts/setup-cicd.sh
```

This will:
- Configure git remotes for staging and production
- Set up your Hugging Face username
- Create necessary branches
- Update all scripts with your username

## Daily Workflow

### 1. Test Locally

Before deploying, run tests:

```bash
# Run automated tests
python scripts/test_local.py

# Test web UI manually
streamlit run app.py

# Test CLI manually
python main_interactive.py
```

### 2. Deploy to Staging

Test your changes on staging first:

**Windows:**
```cmd
scripts\deploy-staging.bat "Your commit message"
```

**Mac/Linux/WSL:**
```bash
./scripts/deploy-staging.sh "Your commit message"
```

Then visit your staging Space and test thoroughly.

### 3. Deploy to Production

Once staging tests pass:

**Windows:**
```cmd
scripts\deploy-production.bat
```

**Mac/Linux/WSL:**
```bash
./scripts/deploy-production.sh
```

### 4. Deploy to Both (Advanced)

Deploy to staging, test, then production:

**Windows:**
```cmd
scripts\deploy-both.bat "Your commit message"
```

**Mac/Linux/WSL:**
```bash
./scripts/deploy-both.sh "Your commit message"
```

## Script Reference

### setup-cicd (.bat / .sh)
**Purpose:** One-time setup of CI/CD pipeline
**Usage:** `scripts\setup-cicd.bat`
**Does:**
- Initializes git if needed
- Adds staging and production remotes
- Updates scripts with your username

### deploy-staging (.bat / .sh)
**Purpose:** Deploy to staging Space for testing
**Usage:** `scripts\deploy-staging.bat "commit message"`
**Does:**
- Commits all changes
- Pushes to staging Space
- Shows staging URL for testing

### deploy-production (.bat / .sh)
**Purpose:** Deploy to production Space (live app)
**Usage:** `scripts\deploy-production.bat`
**Does:**
- Asks for confirmation
- Pushes to production Space
- Monitors deployment

### deploy-both (.bat / .sh)
**Purpose:** Full pipeline - staging → test → production
**Usage:** `scripts\deploy-both.bat "commit message"`
**Does:**
- Deploys to staging
- Waits for your testing
- Asks for confirmation
- Deploys to production

### test_local.py
**Purpose:** Run automated tests before deployment
**Usage:** `python scripts/test_local.py`
**Tests:**
- Module imports
- Configuration loading
- URL validation
- Caption generation
- Transcriber initialization

## Troubleshooting

### "git: command not found"
Install git: https://git-scm.com/downloads

### "Permission denied" (Mac/Linux)
Make scripts executable:
```bash
chmod +x scripts/*.sh
```

### "remote staging does not exist"
Run setup-cicd script first:
```bash
scripts\setup-cicd.bat  # Windows
./scripts/setup-cicd.sh # Mac/Linux
```

### Deployment fails with authentication error
Get your Hugging Face access token:
1. Go to https://huggingface.co/settings/tokens
2. Create new token with "write" permission
3. Use token as password when prompted

### Want to rollback production
```bash
git revert HEAD
git push production main:main
```

## Best Practices

### Always test in staging first
```bash
# ✅ Good
deploy-staging "Fix bug"
# Test on staging
deploy-production

# ❌ Bad
deploy-production  # No testing!
```

### Use descriptive commit messages
```bash
# ✅ Good
deploy-staging "Fix: Caption generation for long videos"

# ❌ Bad
deploy-staging "fix"
```

### Run tests before deploying
```bash
# ✅ Good
python scripts/test_local.py
# If tests pass:
deploy-staging "New feature"

# ❌ Bad
deploy-staging "New feature"  # No testing!
```

## Environment URLs

After setup, your environments will be:

- **Staging:** `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging`
- **Production:** `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber`

Replace `YOUR_USERNAME` with your actual Hugging Face username.

## Zero Downtime Guarantee

When you deploy to production:
1. Old version keeps running
2. New version is built in parallel
3. Once new version is ready, traffic switches instantly
4. No downtime - users never see an interruption

Typical deployment: 5-10 minutes, 0 seconds downtime! ✅

## Need Help?

See the full documentation:
- [CICD_SETUP.md](../CICD_SETUP.md) - Complete CI/CD guide
- [HUGGINGFACE_DEPLOYMENT.md](../HUGGINGFACE_DEPLOYMENT.md) - Hugging Face deployment
- [QUICK_START.md](../QUICK_START.md) - Usage guide

## Quick Command Reference

```bash
# One-time setup
scripts\setup-cicd.bat

# Test locally
python scripts\test_local.py
streamlit run app.py

# Deploy to staging
scripts\deploy-staging.bat "commit message"

# Deploy to production
scripts\deploy-production.bat

# Full pipeline
scripts\deploy-both.bat "commit message"

# Rollback production
git revert HEAD && git push production main:main
```

---

**Happy deploying!** 🚀
