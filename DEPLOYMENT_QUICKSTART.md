# 🚀 Zero-Downtime Deployment - Quick Start

Your complete CI/CD pipeline is ready! Deploy with confidence - no downtime, ever.

## ⚡ Super Quick Start (5 Minutes)

### 1. Run Setup (One-Time)
```bash
# Windows
scripts\setup-cicd.bat

# Mac/Linux/WSL
chmod +x scripts/*.sh
./scripts/setup-cicd.sh
```
Enter your Hugging Face username when prompted.

### 2. Create Two Spaces on Hugging Face

Go to https://huggingface.co/spaces and create:
1. **video-transcriber-staging** (for testing)
2. **video-transcriber** (for production)

Both with:
- SDK: Streamlit
- Hardware: CPU basic (free)

### 3. Get Access Token

1. Go to https://huggingface.co/settings/tokens
2. Create new token
3. Name: "deploy"
4. Role: "write"
5. **Copy the token!**

### 4. Deploy!

```bash
# Test locally first
python scripts/test_local.py

# Deploy to staging
scripts\deploy-staging.bat "Initial deployment"  # Windows
./scripts/deploy-staging.sh "Initial deployment"  # Mac/Linux

# Wait 5-10 mins, test staging, then deploy to production
scripts\deploy-production.bat  # Windows
./scripts/deploy-production.sh  # Mac/Linux
```

When prompted for password, **paste your access token** (not your password).

**Done!** Your app is live with zero downtime! 🎉

---

## 📋 Daily Workflow

### Make Changes → Test → Deploy

```bash
# 1. Develop locally
code .  # Make your changes
streamlit run app.py  # Test locally

# 2. Deploy to staging
scripts\deploy-staging.bat "Fix: Your change description"

# 3. Test on staging
# Visit https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging
# Test thoroughly!

# 4. Deploy to production (if tests pass)
scripts\deploy-production.bat

# Done! Zero downtime ✅
```

---

## 🎯 Key Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `scripts\deploy-staging.bat "msg"` | Deploy to staging | Every time you make changes |
| `scripts\deploy-production.bat` | Deploy to production | After staging tests pass |
| `scripts\deploy-both.bat "msg"` | Full pipeline | When confident about changes |
| `python scripts\test_local.py` | Run automated tests | Before any deployment |

---

## ✅ Zero-Downtime Guarantee

**How it works:**
1. You push code to production
2. Old version keeps running (users happy ✅)
3. New version builds in parallel
4. Once ready, instant switch
5. Old version shut down

**Result:** Users never see downtime, ever!

**Typical timeline:**
- 0:00 - Push code
- 0:00-0:10 - Old version serving users ✅
- 0:10 - Switch to new version ✅
- 0:10+ - New version serving users ✅

**Downtime: 0 seconds!** 🎉

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Your Computer (Development)            │
│  - Make changes                         │
│  - Test locally                         │
│  - Run tests                            │
└───────────────┬─────────────────────────┘
                │
                │ git push staging
                ↓
┌─────────────────────────────────────────┐
│  Staging Space (Testing)                │
│  - Try out changes                      │
│  - Test with real data                  │
│  - Verify everything works              │
│  ✓ Safe to break                        │
└───────────────┬─────────────────────────┘
                │
                │ Tests pass? Deploy!
                │ git push production
                ↓
┌─────────────────────────────────────────┐
│  Production Space (Live)                │
│  - User-facing app                      │
│  - Zero downtime updates                │
│  - Always stable                        │
│  ✓ Never breaks                         │
└─────────────────────────────────────────┘
```

---

## 📊 Cost Breakdown

| Item | Cost | Details |
|------|------|---------|
| **Staging Space** | **$0/month** | Free CPU tier (16GB RAM) |
| **Production Space** | **$0/month** | Free CPU tier (16GB RAM) |
| **Total** | **$0/month** | 100% FREE! 🎉 |

**Optional GPU upgrade:** $0.60/hour only when processing (production only).

---

## 🆘 Common Issues

### "fatal: remote staging does not exist"
**Solution:** Run setup script first
```bash
scripts\setup-cicd.bat  # Windows
./scripts/setup-cicd.sh # Mac/Linux
```

### "Authentication failed"
**Solution:** Use access token, not password
1. Get token: https://huggingface.co/settings/tokens
2. When prompted for password, paste the **token**

### Deployment stuck/slow
**Solution:** Normal! First deployment takes 10 minutes (downloading Whisper model). Subsequent deployments: 3-5 minutes.

### Want to rollback
**Solution:**
```bash
git revert HEAD
git push production main:main
```

### Tests failing
**Solution:** Fix issues before deploying
```bash
python scripts/test_local.py  # See what's failing
# Fix the issues
# Try again
```

---

## 📚 Full Documentation

Need more details?

- **[CICD_SETUP.md](CICD_SETUP.md)** - Complete CI/CD guide with advanced features
- **[HUGGINGFACE_DEPLOYMENT.md](HUGGINGFACE_DEPLOYMENT.md)** - Detailed Hugging Face deployment
- **[scripts/README.md](scripts/README.md)** - All deployment scripts explained
- **[QUICK_START.md](QUICK_START.md)** - How to use the app

---

## 🎓 Pro Tips

### Tip 1: Always test in staging first
```bash
# ✅ Good
deploy-staging "New feature"  # Test here first
deploy-production             # Then go live

# ❌ Bad
deploy-production  # YOLO? No!
```

### Tip 2: Use descriptive commit messages
```bash
# ✅ Good
deploy-staging "Fix: Caption generation for videos >10min"

# ❌ Bad
deploy-staging "stuff"
```

### Tip 3: Run tests before deploying
```bash
# ✅ Good
python scripts/test_local.py  # Tests pass? Deploy!
deploy-staging "Feature X"

# ❌ Bad
deploy-staging "Feature X"  # Hope it works!
```

### Tip 4: Monitor your deployments
1. Go to your Space on Hugging Face
2. Click "Logs" tab
3. Watch build progress
4. See errors in real-time

### Tip 5: Keep staging and production in sync
After successful production deployment:
```bash
git checkout staging
git merge main
```

---

## 🌟 Your URLs

After setup, bookmark these:

**Staging (Testing):**
```
https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber-staging
```

**Production (Live):**
```
https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber
```

Replace `YOUR_USERNAME` with your actual Hugging Face username.

---

## 🎯 Summary

### Setup (Once):
1. Run `scripts\setup-cicd.bat`
2. Create two Spaces on Hugging Face
3. Get access token

### Daily Workflow:
1. Develop locally
2. Test locally
3. Deploy to staging
4. Test on staging
5. Deploy to production
6. **Zero downtime!** ✅

### Key Benefits:
- ✅ **No downtime** - users never interrupted
- ✅ **Safe testing** - staging environment for experiments
- ✅ **Fast iteration** - deploy in minutes
- ✅ **Free** - $0/month for both environments
- ✅ **Automated** - scripts handle everything
- ✅ **Rollback** - easy to revert if needed

---

**You're ready to deploy with confidence!** 🚀

Questions? Check the full docs or run `python scripts/test_local.py` to verify everything works.

**Next command:**
```bash
scripts\setup-cicd.bat  # Start here!
```
