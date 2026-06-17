"""Application configuration settings."""

import os
from pathlib import Path

# App directory (where config.py is located)
APP_DIR = Path(__file__).resolve().parent

# Base directory (project root)
BASE_DIR = APP_DIR.parent

# Application settings
APP_NAME = "Web Tool Set"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "A collection of network diagnostic tools"


def get_positive_int_env(name: str, default: int) -> int:
    """Read a positive integer from an environment variable."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc

    if value < 1:
        raise ValueError(f"{name} must be a positive integer")

    return value


# Rate limiting
RATE_LIMIT_PER_MINUTE = get_positive_int_env("RATE_LIMIT_PER_MINUTE", 60)

# Templates and static files (relative to app directory)
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

# Logging
LOG_CONFIG_FILE = APP_DIR / "logging.yml"
LOG_DIR = BASE_DIR / "log"
