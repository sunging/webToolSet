"""Application configuration settings."""

from pathlib import Path

# App directory (where config.py is located)
APP_DIR = Path(__file__).resolve().parent

# Base directory (project root)
BASE_DIR = APP_DIR.parent

# Application settings
APP_NAME = "Web Tool Set"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "A collection of network diagnostic tools"

# Rate limiting
RATE_LIMIT_PER_MINUTE = 60

# Templates and static files (relative to app directory)
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

# Logging
LOG_CONFIG_FILE = APP_DIR / "logging.yml"
LOG_DIR = BASE_DIR / "log"
