# 🚀 Start Here - Quick Access Guide

## Local Network Hosting (Right Now!)

### Windows Users:
```cmd
start_local_network.bat
```

### Mac/Linux Users:
```bash
chmod +x start_local_network.sh
./start_local_network.sh
```

**The script will show you the URL to share with other devices on your network!**

---

## What Happens Next

### On Your Computer:
1. The script starts
2. Shows your local IP address
3. Opens the app automatically
4. Access at: `http://localhost:8501`

### On Other Devices (Phone, Tablet, Other PCs):
1. Make sure they're on the **same WiFi**
2. Open web browser
3. Enter: `http://YOUR_IP:8501` (script shows your IP)
4. Use the app!

Example: If your IP is `192.168.1.100`, use `http://192.168.1.100:8501`

---

## Quick Test

### 1. Start the server:
```cmd
start_local_network.bat
```

### 2. On this computer:
Open browser → `http://localhost:8501`

### 3. On your phone:
- Connect to same WiFi
- Open browser → `http://YOUR_IP:8501` (from script output)
- Test with a YouTube URL!

---

## Features Available

✅ **Single URL Processing**
- Instagram Reels
- YouTube Videos
- Generate captions (SRT/VTT)

✅ **CSV Batch Processing**
- Upload CSV with multiple URLs
- Process all at once
- **Download All button** includes TXT, SRT, VTT files in ZIP

✅ **All Devices Can:**
- Process videos
- Download files
- Configure settings
- Generate captions

---

## Stop the Server

Press `Ctrl+C` in the terminal/command prompt window

---

## Troubleshooting

### Can't access from phone?

**Check:**
1. ✅ Same WiFi network?
2. ✅ Firewall blocking? (See LOCAL_NETWORK_GUIDE.md)
3. ✅ Correct IP address?
4. ✅ Server still running?

**Quick fix:**
```cmd
# Windows - Allow through firewall (Run as Administrator)
netsh advfirewall firewall add rule name="Streamlit" dir=in action=allow protocol=TCP localport=8501
```

---

## Next Steps

### Currently Using:
- ✅ Local network access
- ✅ WiFi-only
- ✅ Private and secure
- ✅ Uses your hardware

### Want Internet Access?

Deploy to Hugging Face (FREE):
1. Read `DEPLOYMENT_QUICKSTART.md`
2. Run `scripts\setup-cicd.bat`
3. Access from anywhere!
4. Still keep local version for privacy

---

## Quick Reference

| Location | URL | Access |
|----------|-----|--------|
| **This computer** | `http://localhost:8501` | Direct |
| **Other devices** | `http://YOUR_IP:8501` | Same WiFi |
| **From internet** | Deploy to Hugging Face | Anywhere |

---

## Documentation

- **LOCAL_NETWORK_GUIDE.md** - Complete local hosting guide
- **DEPLOYMENT_QUICKSTART.md** - Deploy to internet (Hugging Face)
- **QUICK_START.md** - How to use the app
- **CICD_SETUP.md** - Zero-downtime deployments

---

## Summary

### To Start:
```cmd
start_local_network.bat
```

### To Access:
- **You:** `http://localhost:8501`
- **Others:** `http://YOUR_IP:8501` (same WiFi)

### To Stop:
```
Ctrl+C
```

**That's it! Enjoy your local network transcriber!** 🎉
