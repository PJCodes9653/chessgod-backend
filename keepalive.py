import time
import requests
import os
from datetime import datetime

# URL of your Render service (you'll update this after deployment)
SERVICE_URL = os.getenv('SERVICE_URL', 'YOUR_RENDER_URL_HERE')
PING_INTERVAL = 600  # 10 minutes in seconds

def ping_server():
    try:
        response = requests.get(SERVICE_URL)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if response.status_code == 200:
            print(f"[{now}] Server pinged successfully")
        else:
            print(f"[{now}] Server responded with status {response.status_code}")
    except Exception as e:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Error pinging server: {str(e)}")

def main():
    print("Starting keepalive bot...")
    print(f"Target server: {SERVICE_URL}")
    print(f"Ping interval: {PING_INTERVAL} seconds")
    
    while True:
        ping_server()
        time.sleep(PING_INTERVAL)

if __name__ == "__main__":
    main()