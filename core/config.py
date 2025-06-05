import os
from pathlib import Path

MITCH_ROOT = os.getenv("MITCH_ROOT", Path(__file__).resolve().parents[1])
