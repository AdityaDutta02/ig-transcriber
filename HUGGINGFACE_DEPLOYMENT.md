# Deploying to Hugging Face Spaces

Complete guide to deploy your Video Transcriber app to Hugging Face Spaces for **FREE**.

## Why Hugging Face Spaces?

- ✅ **FREE tier**: 2 vCPU + 16GB RAM (perfect for Whisper base model)
- ✅ **Built for ML apps**: Optimized for Streamlit + ML models
- ✅ **Easy deployment**: Git push workflow
- ✅ **Automatic HTTPS**: Free SSL certificate
- ✅ **Optional GPU**: Upgrade to GPU for $0.60/hour when needed
- ✅ **Persistent storage**: Keep your models cached

## Prerequisites

1. Hugging Face account (free): https://huggingface.co/join
2. Git installed on your computer
3. Your project ready (already done!)

## Step-by-Step Deployment

### Step 1: Create Hugging Face Space

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in the details:
   - **Space name**: `video-transcriber` (or your preferred name)
   - **License**: `MIT`
   - **Select SDK**: `Streamlit`
   - **Hardware**: `CPU basic (free)` (2 vCPU + 16GB RAM)
   - **Visibility**: `Public` (or Private if you prefer)
4. Click **"Create Space"**

### Step 2: Prepare Your Repository

Your project is already prepared! Just need to add a few Hugging Face-specific files.

**Create `README.md` for Hugging Face** (at project root):

```markdown
---
title: Video Transcriber
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: "1.28.0"
app_file: app.py
pinned: false
---

# Video Transcriber

Download and transcribe Instagram Reels & YouTube videos with automatic caption generation.

## Features

- 🎥 Download videos from Instagram & YouTube
- 🎤 Transcribe audio using Whisper AI
- 📝 Generate SRT/VTT subtitles
- 🌍 Multi-language support (100+ languages)
- 📦 Batch processing with CSV
- 💾 Download transcriptions & captions

## Usage

1. Enter a video URL or upload a CSV file
2. Configure transcription settings
3. Process and download results
```

**Create `.spacesignore`** (to exclude unnecessary files):

```
venv/
.git/
.gitignore
.env
data/temp/*
data/output/*
logs/*
*.pyc
__pycache__/
.DS_Store
```

### Step 3: Update requirements.txt

Hugging Face Spaces needs specific versions. Update your `requirements.txt`:

```txt
streamlit==1.28.0
yt-dlp>=2023.10.13
faster-whisper>=1.0.0
torch>=2.0.0,<2.6.0
torchaudio>=2.0.0,<2.6.0
pandas>=2.0.0,<2.3.0
pyyaml>=6.0.1
tqdm>=4.66.0
python-dotenv>=1.0.0
pydantic>=2.5.0,<2.10.0
pydantic-settings>=2.1.0,<2.7.0
loguru>=0.7.2
requests>=2.31.0
aiohttp>=3.9.0
validators>=0.22.0
ffmpeg-python>=0.2.0
```

### Step 4: Create packages.txt (for system dependencies)

Create `packages.txt` at project root:

```
ffmpeg
```

### Step 5: Push to Hugging Face

#### Option A: Direct Git Push (Recommended)

1. **Initialize git in your project** (if not already done):
   ```bash
   cd instagram-reel-transcriber
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Add Hugging Face remote**:
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber
   ```
   Replace `YOUR_USERNAME` with your Hugging Face username.

3. **Push to Hugging Face**:
   ```bash
   git push hf main
   ```

   You'll be prompted for credentials:
   - **Username**: Your Hugging Face username
   - **Password**: Use your **Access Token** (not your password)

   To get your access token:
   - Go to https://huggingface.co/settings/tokens
   - Click "New token"
   - Name: "spaces-deploy"
   - Role: "write"
   - Copy the token and paste when prompted

#### Option B: Upload Files Manually

1. Go to your Space: `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber`
2. Click "Files" tab
3. Click "Add file" → "Upload files"
4. Upload all your project files (except venv/, .git/, data/)
5. Click "Commit changes to main"

### Step 6: Configure Secrets (Optional)

If you need environment variables:

1. Go to your Space settings
2. Click "Settings" → "Repository secrets"
3. Add any secrets you need (API keys, etc.)

### Step 7: Monitor Deployment

1. Your Space will automatically build and deploy
2. Watch the build logs in the "Logs" tab
3. First build takes 5-10 minutes (downloading Whisper model)
4. Once complete, your app will be live!

Your app URL: `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber`

## Configuration

### Model Selection

By default, the app uses Whisper `base` model (good balance of speed/accuracy).

To change the model, edit `config/config.yaml`:

```yaml
transcription:
  model: "base"  # Options: tiny, base, small, medium, large
  device: "cpu"  # Use CPU on Hugging Face free tier
  compute_type: "int8"  # int8 for CPU, float16 for GPU
```

**Model Size Comparison:**

| Model  | Size  | RAM    | Speed      | Accuracy |
|--------|-------|--------|------------|----------|
| tiny   | 75MB  | ~1GB   | Very Fast  | Good     |
| base   | 142MB | ~2GB   | Fast       | Better   |
| small  | 466MB | ~4GB   | Medium     | Good     |
| medium | 1.5GB | ~8GB   | Slow       | Great    |
| large  | 3GB   | ~12GB  | Very Slow  | Best     |

**For Hugging Face free tier (16GB RAM)**, use `base` or `small` model.

### GPU Upgrade (Optional)

If you need faster transcription:

1. Go to Space settings
2. Change hardware to "GPU T4 small" ($0.60/hour)
3. Update `config/config.yaml`:
   ```yaml
   transcription:
     device: "cuda"
     compute_type: "float16"
   ```

## Troubleshooting

### Build Fails with Memory Error

- **Solution**: Use smaller Whisper model (`tiny` or `base`)
- Edit `config/config.yaml` and change `model: "tiny"`

### App Times Out During Transcription

- **Solution**:
  1. Use smaller model
  2. Or upgrade to GPU hardware

### "Module not found" Error

- **Solution**: Make sure all dependencies are in `requirements.txt`
- Check build logs for missing packages

### FFmpeg Not Found

- **Solution**: Make sure `packages.txt` exists with `ffmpeg` in it

### Download Fails

- **Solution**: Some videos may be geo-restricted or require authentication
- Try with different video URLs

## Updating Your Deployment

To update your deployed app:

```bash
# Make your changes
git add .
git commit -m "Update description"
git push hf main
```

The Space will automatically rebuild and redeploy.

## Monitoring Usage

1. Go to your Space page
2. View "Activity" tab for usage stats
3. Monitor "Logs" for errors

## Costs

**FREE Tier:**
- Unlimited public apps
- 2 vCPU + 16GB RAM
- Perfect for personal/demo use

**GPU Upgrade (Optional):**
- T4 GPU: $0.60/hour (only charged when app is active)
- A10G GPU: $1.50/hour (for large models)

## Custom Domain (Optional)

To use your own domain:

1. Go to Space settings
2. Click "Custom domain"
3. Follow instructions to set up DNS

## Alternative: Deploy to Your Own Server

If you prefer self-hosting, see `DEPLOYMENT.md` for Docker deployment instructions.

## Support

- Hugging Face Spaces Docs: https://huggingface.co/docs/hub/spaces
- Streamlit Docs: https://docs.streamlit.io
- Project Issues: Create an issue in your repository

## Next Steps

1. ✅ Deploy to Hugging Face Spaces
2. Test with sample videos
3. Share your Space URL
4. Monitor usage and optimize settings
5. Consider GPU upgrade for production use

---

**Your app will be live at:** `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber`

Enjoy your deployed Video Transcriber! 🎉
