import uvicorn
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from pyngrok import ngrok, conf

def start_public_server():
    # 1. Setup ngrok
    print("--- INVESTOR RADAR PUBLIC ACCESS ---")
    
    # Optional: Set auth token if env var exists
    auth_token = os.environ.get("NGROK_AUTH_TOKEN")
    if auth_token:
        ngrok.set_auth_token(auth_token)
    
    # Open a HTTP tunnel on the default port 8000
    # http_tunnel = ngrok.connect(8000)
    # public_url = http_tunnel.public_url

    try:
        http_tunnel = ngrok.connect(8000)
        public_url = http_tunnel.public_url
        print(f"\n[SUCCESS] Public URL: {public_url}")
        print(f"[INFO] Dashboard available at: {public_url}/dashboard")
        print("\n[SECURITY] Basic Auth Enabled")
        print("           Username: admin")
        print("           Password: radar")
        print("           (Set RADAR_USERNAME/RADAR_PASSWORD env vars to change)")
        print("\n------------------------------------\n")
    except Exception as e:
        print(f"\n[ERROR] Could not connect to ngrok: {e}")
        print("Ensure you have an internet connection.")
        print("If you haven't, sign up at ngrok.com and run: ngrok config add-authtoken <TOKEN>")
        sys.exit(1)

    # 2. Start Uvicorn
    # We run app:app on localhost:8000, which ngrok forwards
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    start_public_server()
