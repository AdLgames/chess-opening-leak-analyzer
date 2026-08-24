"""Chess opening leak analyzer: PGN folder -> Lichess Explorer + Stockfish -> CSV report."""
from .analyze import analyze, build_nodes  # noqa: F401
from .engine import EngineAnalyzer, find_engine  # noqa: F401
from .explorer import OpeningExplorer  # noqa: F401
from .pgn_loader import load_games, find_pgn_files, detect_main_player  # noqa: F401

__version__ = "1.0.0"
