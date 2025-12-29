# Local Network Deployment Guide

Host your Video Transcriber on your local network so all devices (phones, tablets, other computers) can access it.

## Quick Start

### Windows:
```cmd
start_local_network.bat
```

### Mac/Linux/WSL:
```bash
chmod +x start_local_network.sh
./start_local_network.sh
```

The script will show you the URLs to access the app!

## What You Get

### On Your Computer:
```
http://localhost:8501
```

### From Other Devices (Phone, Tablet, Other PCs):
```
http://YOUR_IP:8501
```
Example: `http://192.168.1.100:8501`

## Step-by-Step Setup

### 1. Find Your Local IP Address

**Windows:**
```cmd
ipconfig
```
Look for "IPv4 Address" under your network adapter (usually WiFi or Ethernet).
Example: `192.168.1.100`

**Mac:**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Linux/WSL:**
```bash
hostname -I
```

### 2. Start the Server

Run the start script:

**Windows:**
```cmd
start_local_network.bat
```

**Mac/Linux:**
```bash
./start_local_network.sh
```

You'll see output like:
```
========================================
  Video Transcriber - Local Network
========================================

Starting Streamlit on local network...

Your app will be accessible at:

  On this computer:
  http://localhost:8501

  From other devices on your network:
  http://192.168.1.100:8501

========================================

Press Ctrl+C to stop the server
```

### 3. Access from Other Devices

**On your phone/tablet/other computer:**
1. Make sure the device is on the **same WiFi network**
2. Open a web browser
3. Enter: `http://YOUR_IP:8501` (replace YOUR_IP with your actual IP)
4. The app loads - use it just like on your computer!

## Firewall Configuration

If other devices can't connect, you may need to allow the app through your firewall:

### Windows Firewall:

1. **Windows Security** → **Firewall & network protection**
2. Click **"Allow an app through firewall"**
3. Click **"Change settings"** (may need admin)
4. Click **"Allow another app"**
5. Browse to Python executable (usually `C:\Python311\python.exe`)
6. Check both **Private** and **Public** networks
7. Click **OK**

**Or use command (Run as Administrator):**
```cmd
netsh advfirewall firewall add rule name="Streamlit App" dir=in action=allow protocol=TCP localport=8501
```

### Mac Firewall:

1. **System Preferences** → **Security & Privacy** → **Firewall**
2. Click **Firewall Options**
3. Click **+** to add Python
4. Allow incoming connections

### Linux (UFW):

```bash
sudo ufw allow 8501/tcp
sudo ufw reload
```

## Using the App on Network

Once connected, all devices can:

✅ **Process Single URLs**
- Paste Instagram or YouTube URL
- Generate transcriptions and captions
- Download TXT, SRT, VTT files

✅ **Batch Process CSV Files**
- Upload CSV with multiple URLs
- Process all videos
- Download ZIP with all files

✅ **Configure Settings**
- Change Whisper model
- Adjust caption settings
- Customize output

## Performance Considerations

### Processing happens on the host computer:
- CPU/GPU usage is on your PC, not the mobile device
- Mobile devices just display the interface
- All heavy processing (downloading, transcription) runs on your computer

### Recommendations:
- **Host computer**: Keep it plugged in during heavy processing
- **Network**: Use WiFi for best experience (not mobile data)
- **Multiple users**: Can access simultaneously, but processing is queued

## Security Notes

### Local Network Only:
- ✅ App is only accessible on your local network (WiFi)
- ✅ Not accessible from the internet
- ✅ Safe for home/office use

### Making it Internet-Accessible (Advanced):
If you want access from anywhere:
1. **Not recommended** for local setup (security risks)
2. **Better option**: Deploy to Hugging Face Spaces (FREE, secure)
3. See `HUGGINGFACE_DEPLOYMENT.md` for internet deployment

## Troubleshooting

### "Can't connect from phone"

**Check 1: Same network?**
- Make sure phone and computer are on the same WiFi network
- Not on mobile data

**Check 2: Correct IP?**
- Verify IP address hasn't changed
- Run `ipconfig` (Windows) or `ifconfig` (Mac) again

**Check 3: Firewall blocking?**
- Temporarily disable firewall to test
- If it works, add firewall rule (see above)

**Check 4: Server running?**
- Make sure the start script is still running on your computer
- You should see terminal/command prompt window open

### "Connection refused"

**Solution 1: Restart the server**
```cmd
# Stop: Press Ctrl+C
# Start again:
start_local_network.bat
```

**Solution 2: Check port 8501 is free**
```cmd
# Windows
netstat -ano | findstr :8501

# Mac/Linux
lsof -i :8501

# If something is using port 8501, kill it or use different port:
streamlit run app.py --server.address 0.0.0.0 --server.port 8502
```

### "Site can't be reached"

**Check:** Is your computer's WiFi adapter enabled?
- Make sure laptop WiFi is on (not just Ethernet)
- Make sure not in Airplane mode

### App is slow from other devices

**Normal:** Processing happens on host computer
- Transcription speed depends on your computer's CPU/GPU
- Network speed doesn't affect transcription
- Downloads might be slower over WiFi

## Advanced Configuration

### Change Port:

Edit the start script or run manually:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 9000
```

Access at: `http://YOUR_IP:9000`

### Add Authentication (Streamlit):

Create `.streamlit/secrets.toml`:

```toml
password = "your_password_here"
```

Update `app.py` to check password (requires code changes).

### Keep Server Running (Background):

**Windows (using pythonw):**
```cmd
pythonw -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

**Mac/Linux (using nohup):**
```bash
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 &
```

**Better: Use Docker** (see below)

## Using Docker for Local Network

Docker provides better stability for long-running local servers:

### 1. Start with Docker:
```bash
docker-compose up -d
```

### 2. Access on network:
- Same URLs: `http://YOUR_IP:8501`
- Docker handles port mapping automatically

### 3. View logs:
```bash
docker-compose logs -f
```

### 4. Stop server:
```bash
docker-compose down
```

**Benefits of Docker:**
- ✅ Runs in background
- ✅ Auto-restarts if crashes
- ✅ Isolated environment
- ✅ Easy to update
- ✅ Resource limits

## Mobile Device Tips

### iOS (iPhone/iPad):
1. Open Safari
2. Enter `http://YOUR_IP:8501`
3. Tap Share → Add to Home Screen (for quick access)

### Android:
1. Open Chrome
2. Enter `http://YOUR_IP:8501`
3. Menu → Add to Home Screen

### Works great on tablets:
- Larger screen for CSV processing
- Easy drag-and-drop file uploads
- Full functionality

## Comparison: Local vs Cloud

| Feature | Local Network | Hugging Face Cloud |
|---------|--------------|-------------------|
| **Setup** | 2 minutes | 15 minutes |
| **Cost** | FREE | FREE |
| **Speed** | Your hardware | Cloud hardware |
| **Access** | WiFi only | Anywhere |
| **Uptime** | When PC on | 24/7 |
| **Privacy** | Totally private | Public/Private space |
| **Best for** | Home/Office | Internet access needed |

**Use Local When:**
- ✅ Privacy is critical
- ✅ Only need access at home/office
- ✅ Want to use your GPU
- ✅ No internet dependency

**Use Cloud When:**
- ✅ Need access from anywhere
- ✅ Want 24/7 availability
- ✅ Multiple users outside your network
- ✅ Don't want to keep computer on

## Example Use Cases

### Home Office Setup:
```
Desktop (Windows PC) → Running server
├─ Laptop → Access via http://192.168.1.100:8501
├─ iPhone → Access via Safari
├─ iPad → Process CSV files
└─ Smart TV Browser → View results
```

### Coffee Shop / Temporary:
```
Your laptop creates hotspot
Other devices connect to your hotspot
Access via your laptop's hotspot IP
```

### Office / Small Team:
```
One powerful desktop runs the server
Team members access from their devices
Process videos together
Share results via network drives
```

## Next Steps

### Currently Running Locally?

**To deploy to internet (Hugging Face):**
1. See `DEPLOYMENT_QUICKSTART.md`
2. Run `scripts\setup-cicd.bat`
3. Deploy in 15 minutes
4. Access from anywhere!

### Want Both?

**Run locally AND on cloud:**
- Local: For private/fast processing
- Cloud: For access anywhere
- Keep both in sync with git

## Summary

**To start on local network:**
```cmd
# Windows
start_local_network.bat

# Mac/Linux
./start_local_network.sh
```

**Access from any device:**
```
http://YOUR_IP:8501
```

**Stop server:**
```
Press Ctrl+C in terminal
```

**That's it!** All devices on your network can now use the app! 🎉

---

**Questions?**
- Local network issues? Check Troubleshooting section above
- Want internet access? See `HUGGINGFACE_DEPLOYMENT.md`
- Need help? Check `QUICK_START.md` for usage guide
