"""Centralized configuration for the phishing detection system.

All thresholds, model paths, and tunable parameters are defined here so they
can be imported from a single location across the backend and pipeline modules.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# --- Model Paths ---
EMAIL_MODEL_PATH: str = os.environ.get("EMAIL_MODEL_PATH", "models/email-roberta")
URL_MODEL_PATH: str = os.environ.get("URL_MODEL_PATH", "models/url-roberta")

# --- Classification Thresholds ---
# These thresholds control when the system flags content as phishing or spam.
# The aggregator uses URL_PHISHING_OVERRIDE_THRESHOLD to decide when a URL
# result is confident enough to override the email model's verdict.
EMAIL_THRESHOLD: float = float(os.environ.get("EMAIL_THRESHOLD", "0.7"))
URL_THRESHOLD: float = float(os.environ.get("URL_THRESHOLD", "0.85"))
URL_PHISHING_OVERRIDE_THRESHOLD: float = float(
    os.environ.get("URL_PHISHING_OVERRIDE_THRESHOLD", "0.80")
)

# --- Inference ---
MAX_BATCH_SIZE: int = int(os.environ.get("MAX_BATCH_SIZE", "32"))

# --- Security ---
JWT_SECRET: str = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# --- CORS ---
ALLOWED_ORIGINS: list[str] = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8501").split(",")

# --- Enterprise Allowlist ---
KNOWN_SAFE_DOMAINS: set[str] = {
    "fastapi.tiangolo.com",
    "google.com",
    "github.com",
    "microsoft.com",
    "apple.com",
    "linkedin.com",
    "amazon.com",
    "youtube.com",
    "cloudflare.com",
}
