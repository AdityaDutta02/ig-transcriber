# Deployment Guide

This guide covers deploying the Video Transcriber application in various environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Environment Variables](#environment-variables)

## Prerequisites

### System Requirements
- Python 3.11
- FFmpeg
- 4GB+ RAM (8GB+ recommended)
- GPU with CUDA support (optional, for faster transcription)

### For GPU Support
- NVIDIA GPU with CUDA 11.8+ or 12.x
- nvidia-docker runtime (for Docker deployment)

## Local Development

### 1. Clone Repository
```bash
git clone <repository-url>
cd instagram-reel-transcriber
```

### 2. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install PyTorch with CUDA (Optional)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 5. Install FFmpeg
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://www.gyan.dev/ffmpeg/builds/ and add to PATH

### 6. Configure Application
Edit `config/config.yaml` to customize settings:
- Model size (tiny, base, small, medium, large)
- Device (cuda, cpu, auto)
- Compute type (float16, int8, float32)

### 7. Run Web UI
```bash
streamlit run app.py
```

Access at: http://localhost:8501

### 8. Run Interactive CLI
```bash
python main_interactive.py
```

## Docker Deployment

### CPU-Only Deployment

**1. Build Image:**
```bash
docker build -t video-transcriber .
```

**2. Run Container:**
```bash
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name video-transcriber \
  video-transcriber
```

**3. Using Docker Compose:**
```bash
docker-compose up -d
```

### GPU-Enabled Deployment

**1. Install nvidia-docker:**
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**2. Build GPU Image:**
Edit Dockerfile and uncomment the PyTorch CUDA installation line:
```dockerfile
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**3. Run with GPU:**
```bash
docker-compose --profile gpu up -d
```

**Or manually:**
```bash
docker run -d \
  -p 8501:8501 \
  --gpus all \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --name video-transcriber-gpu \
  video-transcriber
```

## Cloud Deployment

### AWS EC2

**1. Launch EC2 Instance:**
- AMI: Deep Learning AMI (Ubuntu)
- Instance type: g4dn.xlarge (or larger for GPU)
- Storage: 50GB+
- Security Group: Allow port 8501

**2. Setup:**
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Clone repository
git clone <repository-url>
cd instagram-reel-transcriber

# Install dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For GPU support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Run application
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

**3. Use systemd for auto-restart:**
```bash
sudo nano /etc/systemd/system/video-transcriber.service
```

```ini
[Unit]
Description=Video Transcriber Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/instagram-reel-transcriber
Environment="PATH=/home/ubuntu/instagram-reel-transcriber/venv/bin"
ExecStart=/home/ubuntu/instagram-reel-transcriber/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-transcriber
sudo systemctl start video-transcriber
```

### Google Cloud Platform (GCP)

**1. Create VM Instance:**
```bash
gcloud compute instances create video-transcriber \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --maintenance-policy=TERMINATE \
  --boot-disk-size=50GB
```

**2. SSH and Setup:**
Follow similar steps as AWS EC2.

### Azure

**1. Create VM:**
- Size: Standard_NC6s_v3 (for GPU)
- Image: Ubuntu 20.04 LTS
- Open port 8501

**2. Setup:**
Follow similar steps as AWS EC2.

### Heroku (CPU-only)

**1. Create Procfile:**
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**2. Create runtime.txt:**
```
python-3.11.0
```

**3. Deploy:**
```bash
heroku create your-app-name
git push heroku main
```

## Environment Variables

Create a `.env` file for environment-specific configuration:

```env
# Application
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Transcription
WHISPER_MODEL=base
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

# Paths
OUTPUT_DIR=data/output
TEMP_DIR=data/temp

# Logging
LOG_LEVEL=INFO
```

Load in application:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Production Best Practices

### 1. Use Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 2. Enable HTTPS

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Set Resource Limits

**Docker:**
```yaml
services:
  video-transcriber:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

### 4. Monitoring

**Add logging:**
```python
from loguru import logger

logger.add("logs/app_{time}.log", rotation="100 MB")
```

**Health endpoint:**
Already included in Streamlit at `/_stcore/health`

### 5. Auto-scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: video-transcriber-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: video-transcriber
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Troubleshooting

### Out of Memory
- Use smaller model (tiny/base instead of large)
- Reduce concurrent workers in config
- Increase system swap space

### Slow Transcription
- Enable GPU support
- Use int8 compute type
- Reduce model size

### FFmpeg Not Found
```bash
# Add to Dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

### CUDA Out of Memory
- Use smaller model
- Set compute_type to "int8"
- Reduce batch size

## Security Considerations

1. **Don't expose directly to internet** - Use reverse proxy
2. **Enable authentication** - Add Streamlit auth
3. **Limit file uploads** - Set max file size in Streamlit config
4. **Use HTTPS** - Always in production
5. **Regular updates** - Keep dependencies updated
6. **Rate limiting** - Implement request throttling
7. **Input validation** - Already included in app

## Support

For issues and questions:
- Check logs: `logs/app.log`
- Review config: `config/config.yaml`
- GPU status: `nvidia-smi`
- System resources: `htop` or `docker stats`

---

Happy Deploying! 🚀
