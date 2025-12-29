#!/bin/bash
# Start Video Transcriber on Local Network
# All devices on your network can access the app

echo ""
echo "========================================"
echo "  Video Transcriber - Local Network"
echo "========================================"
echo ""

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    IP=$(ipconfig getifaddr en0)
    if [ -z "$IP" ]; then
        IP=$(ipconfig getifaddr en1)
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    IP=$(hostname -I | awk '{print $1}')
else
    # WSL or other
    IP=$(ip route get 1 | awk '{print $7;exit}')
fi

echo "Starting Streamlit on local network..."
echo ""
echo "Your app will be accessible at:"
echo ""
echo "  On this computer:"
echo "  http://localhost:8501"
echo ""
echo "  From other devices on your network:"
echo "  http://$IP:8501"
echo ""
echo "========================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Streamlit with network access
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
