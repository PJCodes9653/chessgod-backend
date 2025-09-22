from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from analysis.analyzer import analyze_game
import chess.pgn
import io
import threading
import time
import requests
from datetime import datetime
import os

app = FastAPI()

# For self-pinging
PING_INTERVAL = 300  # 5 minutes in seconds
is_pinging = False
ping_thread = None

def ping_self():
    """Background thread that pings itself every PING_INTERVAL seconds"""
    # Get the URL from environment or default to localhost
    base_url = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:8000')
    
    while True:
        try:
            response = requests.get(f"{base_url}/ping")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if response.status_code == 200:
                print(f"[{now}] Self-ping successful")
            else:
                print(f"[{now}] Self-ping failed with status {response.status_code}")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Self-ping error: {str(e)}")
        
        time.sleep(PING_INTERVAL)

@app.on_event("startup")
def startup_event():
    """Start the self-pinging thread when the app starts"""
    global ping_thread
    if ping_thread is None:
        ping_thread = threading.Thread(target=ping_self, daemon=True)
        ping_thread.start()

# Allow requests from the extension and localhost development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Chess Analyzer Backend running"}

@app.get("/ping")
async def ping():
    """Endpoint for self-pinging to keep the service alive"""
    return {"status": "alive", "time": datetime.now().isoformat()}

@app.post("/analyze")
async def analyze(file: UploadFile, url: str | None = Form(None), depth: str | None = Form(None)):
    """Receive PGN and optional game URL, run Stockfish analysis, return JSON.
    depth parameter controls Stockfish search depth (default: 15, min: 5, max: 25)."""
    pgn_text = (await file.read()).decode("utf-8")
    # Convert depth to int, as Form data comes as string
    depth_int = int(depth) if depth is not None else depth_int
    depth_int = max(5, min(25, depth_int))  # Clamp to valid range
    result = analyze_game(pgn_text, depth=depth_int)

    # Try to extract player names from PGN tags
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        white = game.headers.get('White', '') if game else ''
        black = game.headers.get('Black', '') if game else ''
    except Exception:
        white = ''
        black = ''

    response = {
        "white_name": white,
        "black_name": black,
        "game_url": url or "",
        **result,
    }
    return JSONResponse(content=response)
