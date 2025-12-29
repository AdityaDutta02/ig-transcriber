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

# Video Transcriber 🎬

Professional video transcription tool for Instagram Reels and YouTube videos with automatic caption generation. Built with Whisper AI for accurate multi-language transcription and Streamlit for an intuitive web interface.

## Features

- 🎥 **Multi-Platform Support**: Download from Instagram Reels and YouTube videos
- 🎤 **AI Transcription**: Powered by faster-whisper for accurate transcriptions
- 📝 **Caption Generation**: Automatic SRT and VTT subtitle file creation
- 🌍 **Multi-Language**: Auto-detect and transcribe 100+ languages
- 📊 **Batch Processing**: Process multiple videos from CSV files
- 💻 **Web UI**: Beautiful Streamlit interface for easy use
- 🖥️ **CLI Mode**: Interactive command-line interface for power users
- ⚡ **GPU Acceleration**: Optional CUDA support for faster processing
- 📦 **ZIP Download**: Bulk download all transcriptions and captions
- 🎨 **Customizable Captions**: Configure words per line and lines per caption
- ☁️ **Cloud Ready**: Deploy to Hugging Face Spaces, AWS, or GCP

## Requirements

### System Requirements
- Python 3.11 (required for faster-whisper)
- 4GB RAM minimum (8GB+ recommended for larger models)
- ffmpeg installed
- NVIDIA GPU with CUDA support (optional, for faster processing)

### Hardware Recommendations
- **CPU Only**: Works well with base/small models
- **With GPU**: RTX 3060 or better for faster transcription
- **Cloud**: Hugging Face Spaces (FREE with 16GB RAM)

## Installation

### 1. Clone or Download the Project
```bash
cd instagram-reel-transcriber
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Linux/Mac
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install ffmpeg

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

### 5. Install CUDA (for GPU support)
Follow NVIDIA's official guide: https://developer.nvidia.com/cuda-downloads

### 6. Verify Installation
```bash
# Check Python packages
pip list | grep -E "whisper|torch|yt-dlp"

# Check GPU (if available)
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"

# Check ffmpeg
ffmpeg -version
```

## Quick Start

### Option 1: Web UI (Recommended)

Start the Streamlit web interface:

```bash
streamlit run app.py
```

Then:
1. **Single URL**: Paste an Instagram or YouTube URL
2. **CSV File**: Upload a CSV with multiple URLs
3. **Configure**: Set caption options (words per line, lines per caption)
4. **Process**: Click "Process Video" or "Process CSV"
5. **Download**: Get TXT, SRT, and VTT files

### Option 2: Interactive CLI

Run the interactive command-line interface:

```bash
python main_interactive.py
```

Follow the prompts to:
1. Choose single URL or CSV file
2. Select operations (download, transcribe, both)
3. Configure caption settings
4. Set file cleanup preferences
5. Specify output directory

### CSV Format

Create a CSV file with video URLs:

```csv
url
https://www.instagram.com/reel/xyz123
https://www.youtube.com/watch?v=abc456
https://www.youtube.com/shorts/def789
```

Save it anywhere, you'll be prompted for the path.

## Configuration

### Basic Configuration
Edit `config/config.yaml`:

```yaml
# Input
input:
  csv_path: "data/input/reels.csv"
  url_column: "url"

# Performance
download:
  concurrent_workers: 12  # Adjust based on your system

transcription:
  model: "base"  # tiny, base, small, medium, large
  device: "cuda"  # cuda or cpu
```

### Environment Variables
Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

## Deployment

### Hugging Face Spaces (Recommended - FREE)

Deploy to Hugging Face for free hosting with 16GB RAM:

**See detailed guide:** [HUGGINGFACE_DEPLOYMENT.md](HUGGINGFACE_DEPLOYMENT.md)

Quick deploy:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber
git push hf main
```

Your app will be live at: `https://huggingface.co/spaces/YOUR_USERNAME/video-transcriber`

### Docker Deployment

Deploy with Docker:

```bash
# Build image
docker build -t video-transcriber .

# Run container
docker-compose up
```

Access at: `http://localhost:8501`

**See detailed guide:** [DEPLOYMENT.md](DEPLOYMENT.md) for AWS, GCP, and other platforms.

### Advanced Usage
```bash
# Custom config file
python main.py --config custom_config.yaml

# Verbose logging
python main.py --verbose

# Process with different URL column
python main.py --csv file.csv --column reel_url
```

### Check CSV Status
```python
from csv_status_manager import CSVStatusManager

manager = CSVStatusManager("data/input/reels.csv")
stats = manager.get_processing_stats()

print(f"Total: {stats['total']}")
print(f"Success: {stats['success']}")
print(f"Failed: {stats['failed']}")
print(f"Unprocessed: {stats['unprocessed']}")
```

## Performance Optimization

### For Maximum Speed
1. Use GPU (`device: cuda`)
2. Use `base` or `small` model
3. Set `concurrent_workers: 12-15`
4. Enable `vad_filter: true`

### For Maximum Accuracy
1. Use `medium` or `large` model
2. Set `temperature: 0.0`
3. Increase `beam_size: 5-10`

### Balancing Speed and Accuracy
```yaml
transcription:
  model: "base"           # Good balance
  device: "cuda"          # Use GPU
  compute_type: "float16" # Faster on GPU
  vad_filter: true        # Skip silence
```

## Output Format

### Transcription File
```
=== METADATA ===
URL: https://instagram.com/reel/abc123
Processed: 2024-11-03 14:23:45
Duration: 28.5 seconds
Language: en
Model: whisper-base
Processing Time: 3.2 seconds

=== TRANSCRIPTION ===
Hey everyone, today I'm going to show you...
[Full transcription here]
```

### Processing Report
```json
{
  "total_reels": 100,
  "successful": 95,
  "failed": 5,
  "processing_time": "4m 32s",
  "average_time_per_reel": "2.7s",
  "reels_per_minute": 22.1
}
```

## Troubleshooting

### Common Issues

**1. "CUDA out of memory"**
- Solution: Use smaller model (`tiny` or `base`)
- Or set `device: cpu` in config

**2. "Failed to download reel"**
- Check if reel is public
- Increase `rate_limit_delay`
- Check internet connection

**3. "ffmpeg not found"**
- Install ffmpeg (see installation section)
- Add ffmpeg to system PATH

**4. Slow processing**
- Enable GPU mode
- Use smaller Whisper model
- Increase `concurrent_workers`

### Logs
Check logs for detailed error information:
```bash
# Main log
tail -f logs/app.log

# Errors only
tail -f logs/errors.log

# Failed URLs
cat logs/failed_urls.txt
```

## Project Structure

```
instagram-reel-transcriber/
├── src/                   # Source code
├── data/
│   ├── input/            # Input CSV files
│   ├── temp/             # Temporary downloads
│   └── output/           # Transcriptions and reports
├── logs/                 # Log files
├── config/               # Configuration files
├── tests/                # Unit tests
├── main.py               # Entry point
└── requirements.txt      # Dependencies
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
isort src/
```

### Type Checking
```bash
mypy src/
```

## Cloud Deployment

### Docker
```bash
# Build image
docker build -t reel-transcriber .

# Run container
docker run -v $(pwd)/data:/app/data reel-transcriber
```

### Google Cloud Platform
```bash
# Deploy to Cloud Run
cd deployment/gcp
./deploy.sh
```

### AWS
```bash
# Deploy to ECS
cd deployment/aws
./deploy.sh
```

## Limitations

- Only works with **public** Instagram reels
- No authentication support (to avoid account bans)
- Rate limited to avoid IP blocks
- Private/age-restricted content will be skipped

## Legal Notice

This tool is for educational and research purposes only. Users are responsible for:
- Respecting Instagram's Terms of Service
- Ensuring they have rights to download and process content
- Complying with copyright and data privacy laws
- Using the tool ethically and responsibly

## Performance Benchmarks

| Hardware | Model | Reels/Minute | 100 Reels |
|----------|-------|--------------|-----------|
| RTX 3060 | base  | 20-25        | ~4-5 min  |
| RTX 3060 | small | 15-18        | ~5-7 min  |
| RTX 4090 | base  | 35-40        | ~2.5 min  |
| CPU (8-core) | base | 8-12     | ~8-12 min |

## Contributing

This is an internal tool, but improvements are welcome!

1. Create a feature branch
2. Make your changes
3. Add tests
4. Submit a pull request

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs in `logs/`
3. Contact your team lead

## Roadmap

- [x] Phase 1: Core functionality ✅
  - [x] CSV parsing and validation
  - [x] Parallel downloading
  - [x] GPU-accelerated transcription
  - [x] Error handling and retries
  - [x] CSV status tracking ⭐
  - [x] Auto cleanup ⭐
  - [x] Resume capability ⭐
  - [x] API foundation ⭐
- [ ] Phase 2: Web Deployment (Next)
  - [ ] Web dashboard
  - [ ] File upload interface
  - [ ] Real-time progress tracking
  - [ ] User authentication
  - [ ] Batch management UI
- [ ] Phase 3: Cloud Deployment
  - [ ] GCP deployment
  - [ ] AWS deployment
  - [ ] Auto-scaling
  - [ ] API gateway

## License

Internal tool - All rights reserved

---

**Version**: 1.0.0  
**Last Updated**: November 2024
