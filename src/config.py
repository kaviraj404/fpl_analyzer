import os
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
LOGS_DIR = PROJECT_ROOT / 'logs'

# Database
DATABASE_PATH = DATA_DIR / 'fpl_data.db'

# Logging
LOG_FILE = LOGS_DIR / 'fpl_analyzer.log'

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# FPL API settings
FPL_TIMEOUT = 30  # seconds