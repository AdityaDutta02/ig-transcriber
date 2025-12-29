# Zero-Downtime CI/CD Pipeline for Hugging Face

Complete setup for continuous deployment with staging and production environments - **NO DOWNTIME**.

## Architecture Overview

```
Local Development
      ↓
   Git Push
      ↓
Staging Space (Test) → Verify Changes
      ↓
   Promote
      ↓
Production Space (Live) → Zero Downtime
```

## Strategy: Two Spaces Approach

### Space 1: Staging (Testing)
- URL: `huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging`
- Purpose: Test new features and fixes
- Can break without affecting users
- Fast iteration and testing

### Space 2: Production (Live)
- URL: `huggingface.co/spaces/YOUR_USERNAME/video-transcriber`
- Purpose: Stable, user-facing app
- Only receives tested code
- Always available

## Setup Instructions

### Step 1: Create Two Spaces on Hugging Face

#### Production Space
1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Settings:
   - **Name**: `video-transcriber`
   - **SDK**: `Streamlit`
   - **Hardware**: `CPU basic (free)`
   - **Visibility**: `Public`
4. Click "Create Space"

#### Staging Space
1. Click "Create new Space" again
2. Settings:
   - **Name**: `video-transcriber-staging`
   - **SDK**: `Streamlit`
   - **Hardware**: `CPU basic (free)`
   - **Visibility**: `Public` or `Private` (your choice)
3. Click "Create Space"

### Step 2: Set Up Git Remotes

Run these commands in your project folder:

```bash
cd C:\Users\csp\Documents\Projects\instagram-reel-transcriber

# Initialize git if not done
git init
git add .
git commit -m "Initial commit"

# Add staging remote
git remote add staging https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging

# Add production remote
git remote add production https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber

# Verify remotes
git remote -v
```

### Step 3: Create Deployment Scripts

The deployment scripts are already in your `scripts/` folder (created below).

### Step 4: Set Up Git Branches

```bash
# Create and switch to staging branch
git checkout -b staging

# Create production branch (initially same as staging)
git checkout -b production

# Switch back to main development branch
git checkout -b main
```

## Daily Workflow (Zero Downtime)

### 1. Develop Locally

Make your changes and test locally:

```bash
# Make your code changes
# ... edit files ...

# Test locally
streamlit run app.py

# Or test with CLI
python main_interactive.py
```

### 2. Deploy to Staging for Testing

When ready to test on Hugging Face:

```bash
# Commit your changes
git add .
git commit -m "Fix: Your description here"

# Push to staging
git push staging main:main
```

This deploys to your **staging Space** - production is still running the old version!

### 3. Test on Staging

1. Go to `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging`
2. Wait for build to complete (watch Logs tab)
3. Test your changes thoroughly:
   - Test single URL
   - Test CSV upload
   - Test caption generation
   - Test downloads
4. If issues found → fix locally → repeat step 2

### 4. Deploy to Production (When Ready)

Once staging tests pass:

```bash
# Deploy to production
git push production main:main
```

This deploys to your **production Space** with your tested changes!

**Result**: Production gets updated with zero downtime. Old version runs until new version is built and ready.

## Quick Deployment Scripts

I've created scripts to make this even easier:

### Deploy to Staging
```bash
./scripts/deploy-staging.sh "Your commit message"
```

### Deploy to Production
```bash
./scripts/deploy-production.sh
```

### Deploy to Both (Staging → Production)
```bash
./scripts/deploy-both.sh "Your commit message"
```

## Advanced: Automated Testing Before Production

Add a test step before production deployment:

```bash
# Deploy to staging
./scripts/deploy-staging.sh "New feature"

# Run automated tests on staging
python scripts/test_staging.py

# If tests pass, deploy to production
./scripts/deploy-production.sh
```

## Rollback Strategy

If production deployment has issues:

### Option 1: Quick Rollback
```bash
# Revert to previous commit
git revert HEAD
git push production main:main
```

### Option 2: Rollback to Specific Version
```bash
# Find the good commit
git log

# Reset to that commit
git reset --hard COMMIT_HASH
git push production main:main --force
```

### Option 3: Emergency Rollback
1. Go to your production Space on Hugging Face
2. Click "Files and versions"
3. Click on a previous commit
4. Click "Restore this commit"

## Zero-Downtime Guarantees

### How Hugging Face Ensures Zero Downtime:

1. **Build-then-switch**: New version is built while old version runs
2. **Health checks**: New version must be healthy before switch
3. **Instant switch**: Traffic redirected to new version when ready
4. **No gap**: Old version keeps running until new one is ready

### Typical Deployment Timeline:

```
0:00 - Push to production
0:00 - Old version still serving users ✅
0:01 - Build starts (installing dependencies)
0:05 - Build continues (downloading Whisper model)
0:08 - New version starting up
0:09 - Health check passed
0:10 - Traffic switched to new version ✅
0:10 - Old version shut down
```

**Users experience**: No interruption! Old version runs until new one is ready.

## Best Practices

### 1. Always Test in Staging First
```bash
# ✅ Good
git push staging main:main
# Test on staging
# If good:
git push production main:main

# ❌ Bad
git push production main:main  # No testing!
```

### 2. Use Descriptive Commit Messages
```bash
# ✅ Good
git commit -m "Fix: SRT generation for videos longer than 10 minutes"

# ❌ Bad
git commit -m "fix"
```

### 3. Keep Staging and Production in Sync
```bash
# After successful production deployment
git checkout staging
git merge main
git push staging main:main
```

### 4. Monitor Both Environments
- **Staging**: Check logs for errors during testing
- **Production**: Monitor Activity tab for usage and errors

## Configuration for Multiple Environments

Create environment-specific configs:

### config/config.staging.yaml
```yaml
transcription:
  model: "tiny"  # Faster for testing
  device: "cpu"
  compute_type: "int8"

logging:
  level: "DEBUG"  # More verbose in staging
```

### config/config.production.yaml
```yaml
transcription:
  model: "base"  # Better quality for production
  device: "cpu"
  compute_type: "int8"

logging:
  level: "INFO"  # Less verbose in production
```

## Troubleshooting

### Staging Build Fails
- **Fix locally and redeploy**: Build will retry automatically
- **Check Logs tab**: See detailed error messages
- **No impact**: Production still running fine

### Production Build Fails
- **Old version keeps running**: No downtime!
- **Fix the issue**: Deploy fix to staging first
- **Test and redeploy**: Production will update when build succeeds

### Need to Pause Production
```bash
# Redirect users to maintenance page
# (Create maintenance.py with simple message)
git checkout production
mv app.py app.backup.py
mv maintenance.py app.py
git commit -m "Maintenance mode"
git push production main:main

# When done
mv app.backup.py app.py
rm maintenance.py
git commit -m "Back online"
git push production main:main
```

## Cost Optimization

### Free Tier (Both Spaces)
- Staging: Free (CPU basic)
- Production: Free (CPU basic)
- **Total cost**: $0/month

### With GPU (Optional)
- Staging: Free (test on CPU)
- Production: GPU T4 ($0.60/hour, ~$432/month if always on)
- **Recommendation**: Use GPU only when processing, not idle

### Smart GPU Usage
Enable "Sleep mode" on production Space:
- Space sleeps after 48 hours of inactivity
- Wakes up when user visits (30 seconds)
- Saves GPU costs when not in use

## Monitoring and Alerts

### Monitor Production Health

1. **Activity Tab**: Track usage and errors
2. **Logs Tab**: Real-time logs
3. **Settings > Webhooks**: Get notified on errors (advanced)

### Key Metrics to Watch

- **Build time**: Should be consistent (~10 minutes first time, ~5 minutes after)
- **Response time**: Transcription speed
- **Error rate**: Failed transcriptions
- **Usage**: Number of users

## Summary

### Your Deployment Flow:

```bash
# 1. Develop locally
code .  # Make changes
streamlit run app.py  # Test locally

# 2. Deploy to staging
git add .
git commit -m "Feature: Add new capability"
git push staging main:main

# 3. Test on staging
# Visit staging URL and test thoroughly

# 4. Deploy to production (if tests pass)
git push production main:main

# 5. Verify production
# Visit production URL and verify

# Done! Zero downtime ✅
```

### Time to Deploy:
- **Staging**: 5-10 minutes (initial), 3-5 minutes (subsequent)
- **Production**: 5-10 minutes (initial), 3-5 minutes (subsequent)
- **Downtime**: 0 seconds ✅

### Quick Commands Reference:

```bash
# Deploy to staging
git push staging main:main

# Deploy to production
git push production main:main

# Rollback production
git revert HEAD && git push production main:main

# Check deployment status
# Visit: https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging
# Visit: https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber
```

---

**You now have a professional CI/CD pipeline with zero downtime!** 🚀

Test safely in staging → Deploy confidently to production → Users never see downtime!
