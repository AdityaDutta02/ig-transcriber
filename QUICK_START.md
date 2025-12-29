# 🚀 Quick Start Guide

Get up and running with Video Transcriber in 5 minutes!

## 1️⃣ Web UI (Easiest - Recommended)

### Start the Web Interface

```bash
streamlit run app.py
```

### Open in Browser
Navigate to: **http://localhost:8501**

### Use the Interface
1. **Choose input method:**
   - Single URL: Paste an Instagram or YouTube link
   - CSV File: Upload a file with multiple URLs

2. **Configure operations:**
   - ✅ Download Videos
   - ✅ Transcribe Audio

3. **Click "Process"** and wait for results!

4. **Download transcriptions** directly from the browser

---

## 2️⃣ Interactive CLI

### Run the CLI

```bash
python main_interactive.py
```

### Follow the Prompts

```
How would you like to provide input?
  1. Single URL
  2. CSV file
Enter your choice (1 or 2): 1

Enter video URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ

What operations would you like to perform?
  1. Download only
  2. Transcribe only
  3. Download and Transcribe (recommended)
Enter your choice: 3

What files would you like to keep?
  1. Audio files (.wav)
  2. Video files
  3. Transcription files (.txt)
Choice: 3

Output directory (default: data/output):
[Press Enter for default]
```

That's it! Your transcription will be saved automatically.

---

## 3️⃣ Automated Pipeline

### For Batch Processing

```bash
python main.py --csv data/input/videos.csv
```

### CSV Format

Create `data/input/videos.csv`:
```csv
url
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.instagram.com/reel/Cz123abc/
https://youtu.be/jNQXAC9IVRw
```

### Run and Relax

The pipeline will:
1. ✅ Download all videos
2. ✅ Transcribe them
3. ✅ Save transcriptions to `data/output/transcriptions/`
4. ✅ Clean up temporary files
5. ✅ Show you a summary

---

## 📝 Example Workflow

### Single YouTube Video

**Web UI:**
1. Open http://localhost:8501
2. Paste: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
3. Click "Process Video"
4. Copy or download transcription

**CLI:**
```bash
python main_interactive.py
# Choose: 1 (Single URL)
# Paste URL
# Choose: 3 (Download and Transcribe)
# Choose: 3 (Keep transcriptions only)
# Press Enter for default output
```

### Batch Processing

**Create CSV:**
```bash
echo "url" > videos.csv
echo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" >> videos.csv
echo "https://www.instagram.com/reel/Cz123abc/" >> videos.csv
```

**Process:**
```bash
python main.py --csv videos.csv
```

**Find Results:**
```bash
ls data/output/transcriptions/
# youtube_dQw4w9WgXcQ.txt
# instagram_Cz123abc.txt
```

---

## ⚙️ Configuration

### Change Model (Speed vs Accuracy)

Edit `config/config.yaml`:

```yaml
transcription:
  model: "base"  # Change to: tiny, small, medium, or large
  device: "cuda"  # or "cpu" if no GPU
```

**Quick Guide:**
- `tiny` = Fastest, least accurate
- `base` = **Recommended** for most users
- `medium` = Better accuracy, slower
- `large` = Best accuracy, slowest (requires 10GB VRAM)

### Enable GPU

Already using GPU? Great! Check with:
```bash
python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"
```

Not using GPU? See [README.md](README.md#installation) for setup instructions.

---

## 🎯 Common Tasks

### Transcribe One YouTube Video
```bash
streamlit run app.py
# Enter URL → Click Process → Download
```

### Transcribe Multiple Videos
```bash
# Create videos.csv with URLs
python main.py --csv videos.csv
# Check data/output/transcriptions/
```

### Use Custom Output Directory
```bash
python main_interactive.py
# Follow prompts
# Enter custom directory when asked
```

### Keep Audio Files
```bash
python main_interactive.py
# Choose operations
# Keep: 1,3 (audio + transcriptions)
```

---

## 🐛 Troubleshooting

### "FFmpeg not found"
**Fix:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://www.gyan.dev/ffmpeg/builds/
# Add to PATH
```

### "CUDA out of memory"
**Fix:** Use smaller model in `config/config.yaml`:
```yaml
transcription:
  model: "tiny"  # or "base"
  compute_type: "int8"
```

### "Download failed"
**Fix:** Check:
- URL is valid and public
- Video still exists
- Not rate-limited (wait a minute and retry)

### Web UI won't start
**Fix:**
```bash
# Check if port is in use
netstat -an | findstr "8501"  # Windows
lsof -i :8501  # Linux/Mac

# Use different port
streamlit run app.py --server.port 8502
```

---

## 📚 Next Steps

- ✅ Read full [README.md](README.md) for detailed documentation
- ✅ Check [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- ✅ See [YOUTUBE_INTEGRATION.md](YOUTUBE_INTEGRATION.md) for platform specifics
- ✅ Customize `config/config.yaml` for your needs

---

## 💡 Tips

1. **Start with Web UI** - Easiest to use
2. **Use 'base' model** - Best balance of speed/accuracy
3. **Enable GPU** - 2-3x faster transcription
4. **Batch process** - More efficient for multiple videos
5. **Keep transcriptions only** - Save disk space

---

**Happy Transcribing! 🎉**

Questions? Check the full [README.md](README.md) or open an issue!
