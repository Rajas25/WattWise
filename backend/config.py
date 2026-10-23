"""
WattWise Backend Configuration
================================
All settings are loaded from environment variables with safe local defaults.
Copy .env.example to .env and fill in values before running in any environment.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # Project root (so backend can import utils.py etc.)
    PROJECT_ROOT: str = str(BASE_DIR)

    # Application
    APP_NAME: str = "WattWise API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("WATTWISE_DEBUG", "false").lower() == "true"

    # Database — SQLite file path (configurable via env)
    DATABASE_URL: str = os.getenv(
        "WATTWISE_DATABASE_URL",
        str(BASE_DIR / "data" / "wattwise.db"),
    )

    # JWT Authentication
    # IMPORTANT: Set a strong random SECRET_KEY in .env for any real deployment.
    # The default here is ONLY for local development.
    SECRET_KEY: str = os.getenv(
        "WATTWISE_SECRET_KEY",
        "dev-only-insecure-key-change-in-production",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("WATTWISE_TOKEN_EXPIRE_MINUTES", "60")
    )

    # CORS — allow local frontend origins
    ALLOWED_ORIGINS: list = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",     # VS Code Live Server
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "null",                      # file:// origin (dev only)
    ]

    # Electricity tariff (configurable)
    TARIFF_INR_PER_KWH: float = float(
        os.getenv("WATTWISE_TARIFF_INR_PER_KWH", "8.50")
    )

    # Waste-detection thresholds
    RESIDUAL_THRESHOLD_KW: float = float(
        os.getenv("WATTWISE_RESIDUAL_THRESHOLD_KW", "10.0")
    )
    OCCUPANCY_THRESHOLD: int = int(
        os.getenv("WATTWISE_OCCUPANCY_THRESHOLD", "5")
    )

    # Model artifacts
    MODELS_DIR: str = str(BASE_DIR / "models")
    BEST_MODEL_PATH: str = str(BASE_DIR / "models" / "best_model.joblib")
    METADATA_PATH: str = str(BASE_DIR / "models" / "model_metadata.json")

    # Data
    DATA_DIR: str = str(BASE_DIR / "data")
    ENERGY_DATA_PATH: str = str(BASE_DIR / "data" / "energy_data.csv")

    # Simulator
    SIMULATOR_INTERVAL_SECONDS: int = int(
        os.getenv("WATTWISE_SIMULATOR_INTERVAL", "30")
    )

    # Rate limiting — max login attempts per minute per IP (simple counter)
    LOGIN_RATE_LIMIT: int = int(os.getenv("WATTWISE_LOGIN_RATE_LIMIT", "10"))


settings = Settings()
