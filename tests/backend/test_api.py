from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.conftest import DEMO_PASSWORD, DEMO_USERNAME


# Mock the ML Model so we don't load the real RoBERTa weights during tests
class MockDetector:
    status = "loaded"

    def predict(self, text: str) -> dict:
        is_phish = "fake-bank" in text.lower()
        return {"is_phishing": is_phish, "confidence": 0.99 if is_phish else 0.1, "message": "Mock"}

    def predict_batch(self, texts: list[str]) -> list[dict]:
        return [self.predict(t) for t in texts]


@pytest.fixture
def client():
    # Patch the model loader to return our mock detectors instead
    with patch(
        "backend.main.load_roberta_models",
        return_value={"email": MockDetector(), "url": MockDetector()},
    ):
        # TestClient automatically triggers FastAPI's startup 'lifespan' events
        with TestClient(app) as test_client:
            yield test_client


def test_login_and_batch_predict(client):
    # 1. Login to get token
    login_resp = client.post("/token", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. Test batch predict with the token
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"texts": ["Hello world", "Check out this fake-bank!"], "input_type": "email"}
    resp = client.post("/api/v1/predict/batch", json=payload, headers=headers)

    assert resp.status_code == 200
    results = resp.json().get("results")
    assert len(results) == 2
    assert results[0]["is_phishing"] is False
    assert results[1]["is_phishing"] is True
