import asyncio
import socketio
import requests
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8001"
# Change this to an OTC asset you want to track
ASSET = "#AAPL_otc" 

sio = socketio.AsyncClient()

@sio.event
async def connect():
    print(f"[Socket.IO] Connected to {BASE_URL}")
    # Focus on the asset to start receiving ticks
    print(f"[Socket.IO] Focusing on asset: {ASSET}")
    await sio.emit("focus_asset", {"asset": ASSET})

@sio.on("status")
async def on_status(data):
    print(f"[Socket.IO] Status Update: {data}")

@sio.on("market_data")
async def on_market_data(data):
    ts = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S.%f')[:-3]
    oteo = data.get('oteo_score', 'N/A')
    conf = data.get('confidence', 'N/A')
    rec = data.get('recommended', 'N/A')
    manip = "DETECTED" if data.get('manipulation') else "None"
    
    print(f"[{ts}] {data['asset']} | Price: {data['price']:.5f} | OTEO: {oteo} ({conf}) | REC: {rec} | Manip: {manip}")

@sio.on("warmup_status")
async def on_warmup(data):
    print(f"[Socket.IO] Warmup: {data['ticks_received']}/50 ticks | Ready: {data['ready']}")

async def main():
    # 1. Connect to the server
    try:
        await sio.connect(BASE_URL)
    except Exception as e:
        print(f"Error connecting to Socket.IO: {e}")
        print("Make sure the backend is running on port 8001 (uvicorn app.backend.main:app --port 8001)")
        return

    # 2. Wait for user to connect the broker if not already connected
    print("\n" + "="*50)
    print("STREAMING VERIFICATION READY")
    print("="*50)
    print(f"1. Open a new terminal and run the backend if not already started.")
    print(f"2. Use the Swagger UI at {BASE_URL}/docs to call /api/session/connect with your SSID.")
    print(f"   Or run: curl -X POST {BASE_URL}/api/session/connect -H \"Content-Type: application/json\" -d \"{{\\\"ssid\\\": \\\"YOUR_SSID_HERE\\\"}}\"")
    print("="*50 + "\n")

    try:
        await sio.wait()
    except KeyboardInterrupt:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
