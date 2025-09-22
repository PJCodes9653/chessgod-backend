from fastapi import FastAPI, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from analysis.analyzer import analyze_game
import chess.pgn
import io
import asyncio
import aiohttp
from datetime import datetime
import os

app = FastAPI()

# For self-pinging
PING_INTERVAL = 600  # 10 minutes in seconds
is_pinging = False

async def ping_self():
    """Background task that pings itself every PING_INTERVAL seconds"""
    global is_pinging
    if is_pinging:
        return
    
    is_pinging = True
    
    # Get the URL from environment or default to localhost
    base_url = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:8000')
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(f"{base_url}/ping") as response:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if response.status == 200:
                        print(f"[{now}] Self-ping successful")
                    else:
                        print(f"[{now}] Self-ping failed with status {response.status}")
            except Exception as e:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{now}] Self-ping error: {str(e)}")
            
            await asyncio.sleep(PING_INTERVAL)

@app.on_event("startup")
async def startup_event():
    """Start the self-pinging task when the app starts"""
    asyncio.create_task(ping_self())

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
