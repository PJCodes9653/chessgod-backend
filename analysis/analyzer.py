# backend/analysis/analyzer.py

import os
import platform
import io
from typing import Dict, Any, List

import chess
import chess.pgn
import chess.engine

# -------- CONFIG --------
MATE_SCORE = 100000

CATEGORIES = [
    "brilliant",
    "great",
    "best",
    "excellent",
    "good",
    "book",
    "inaccuracy",
    "mistake",
    "blunder",
    "missed",
]

THRESHOLDS_CP = {
    "great": 10,
    "excellent": 30,
    "good": 75,
    "inaccuracy": 150,
    "mistake": 300,
}


def get_stockfish_path() -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stockfish"))
    if platform.system() == "Windows":
        return os.path.join(base, "stockfish.exe")
    return os.path.join(base, "stockfish")


STOCKFISH_PATH = get_stockfish_path()


def classify_cp_loss(cp_loss: int, is_best_move: bool) -> str:
    if cp_loss == 0 and is_best_move:
        return "best"
    if cp_loss == 0:
        return "great"
    if cp_loss <= THRESHOLDS_CP["great"]:
        return "great"
    if cp_loss <= THRESHOLDS_CP["excellent"]:
        return "excellent"
    if cp_loss <= THRESHOLDS_CP["good"]:
        return "good"
    if cp_loss <= THRESHOLDS_CP["inaccuracy"]:
        return "inaccuracy"
    if cp_loss <= THRESHOLDS_CP["mistake"]:
        return "mistake"
    return "blunder"


def chesscom_accuracy_from_acl(acl: float) -> float:
    """
    Approximate Chess.com-style formula based on curve fit.
    accuracy ≈ 103.3979 − 0.3820659 * ACL − 0.002169231 * ACL^2
    """
    acc = 103.3979 - 0.3820659 * acl - 0.002169231 * (acl ** 2)
    acc = max(0.0, min(100.0, acc))
    return round(acc, 2)


def analyze_game(pgn_text: str, depth: int = 15) -> Dict[str, Any]:
    """Analyze a single PGN game and return per-side statistics.

    Args:
        pgn_text: The PGN text to analyze
        depth: Stockfish search depth (default: 15, min: 5, max: 25)

    Returns:
        Dict with counts and per-category move number lists.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Invalid PGN provided")

    # Initialize stats with counts and lists of move numbers for each category
    stats = {
        "white": {
            "counts": {k: 0 for k in CATEGORIES},
            "moves": {k: [] for k in CATEGORIES},
        },
        "black": {
            "counts": {k: 0 for k in CATEGORIES},
            "moves": {k: [] for k in CATEGORIES},
        },
    }

    total_cp_loss = {"white": 0.0, "black": 0.0}
    total_moves = {"white": 0, "black": 0}

    board = game.board()

    # Verify stockfish exists
    if not os.path.exists(STOCKFISH_PATH):
        raise FileNotFoundError(f"Stockfish not found at {STOCKFISH_PATH}")

    # Use engine context to ensure clean shutdown
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        # Iterate through every move and evaluate before and after the move
        for move in game.mainline_moves():
            mover_color = board.turn
            side = "white" if mover_color == chess.WHITE else "black"
            move_number = board.fullmove_number

            # Safety: skip illegal moves (shouldn't normally happen)
            if not board.is_legal(move):
                # record as missed if you like, but skip for now
                board.push(move)
                continue

            # Engine evaluation before the move (get best move and score)
            try:
                info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
            except Exception:
                # If engine fails, push move and continue
                board.push(move)
                continue

            best_move = None
            if info_before is not None:
                pv = info_before.get("pv")
                if pv:
                    best_move = pv[0]

            score_before_obj = info_before.get("score") if info_before else None
            score_before = None
            if score_before_obj is not None:
                try:
                    score_before = score_before_obj.pov(mover_color).score(mate_score=MATE_SCORE)
                except Exception:
                    score_before = None

            # Play the actual move
            board.push(move)

            # Engine evaluation after the move (from same mover's perspective)
            try:
                info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
            except Exception:
                info_after = None

            score_after_obj = info_after.get("score") if info_after else None
            score_after = None
            if score_after_obj is not None:
                try:
                    score_after = score_after_obj.pov(mover_color).score(mate_score=MATE_SCORE)
                except Exception:
                    score_after = None

            # Compute centipawn loss (non-negative)
            cp_loss = 0.0
            if score_before is not None and score_after is not None:
                try:
                    cp_loss = float(score_before) - float(score_after)
                    if cp_loss < 0:
                        cp_loss = 0.0
                except Exception:
                    cp_loss = 0.0

            # Determine if the move played was the engine's best move
            is_best_move = best_move is not None and move == best_move

            # Classify and record
            cat = classify_cp_loss(int(round(cp_loss)), is_best_move)
            stats[side]["counts"][cat] += 1
            stats[side]["moves"][cat].append(move_number)
            if cat in ("mistake", "blunder"):
                stats[side]["counts"]["missed"] += 1
                stats[side]["moves"]["missed"].append(move_number)

            total_cp_loss[side] += cp_loss
            total_moves[side] += 1

    # Remove accuracy - frontend requested counts and moves only

    return stats
