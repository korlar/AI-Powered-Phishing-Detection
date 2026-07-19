"""Shared test fixtures for the phishing detection project."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

# Read the demo password from the environment (same source as the backend).
# Set DEMO_PASSWORD in your .env file before running tests.
DEMO_PASSWORD: str = os.environ.get("DEMO_PASSWORD", "")
if not DEMO_PASSWORD:
    raise RuntimeError(
        "DEMO_PASSWORD is not set. Add DEMO_PASSWORD=<your-password> to your .env file."
    )

DEMO_USERNAME: str = "admin"


class MockDetector:
    """A lightweight mock that mimics PhishingDetector without loading real models."""

    status = "loaded"

    def predict(self, text: str) -> dict:
        is_phish = "fake-bank" in text.lower() or "phishing" in text.lower()
        return {
            "is_phishing": is_phish,
            "confidence": 0.95 if is_phish else 0.10,
            "message": "Phishing detected" if is_phish else "Content appears safe",
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        return [self.predict(t) for t in texts]

    def explain(self, text: str, target_class: int = None) -> list[dict]:
        words = text.split()[:5]
        return [{"word": w, "importance": 0.5 / (i + 1)} for i, w in enumerate(words)]


@pytest.fixture()
def mock_models():
    """Returns a dict of mock ML models keyed by task name."""
    return {"email": MockDetector(), "url": MockDetector()}


@pytest.fixture()
def client(mock_models):
    """Authenticated FastAPI TestClient with mocked ML models."""
    with patch("backend.main.load_roberta_models", return_value=mock_models):
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture()
def auth_headers(client):
    """Returns Authorization headers from a successful login."""
    resp = client.post("/token", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
