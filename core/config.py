import os

MITCH_ROOT = os.getenv("MITCH_ROOT", "/home/triad/mitch")
DEBUG = os.getenv("MITCH_DEBUG", "false").lower() == "true"
