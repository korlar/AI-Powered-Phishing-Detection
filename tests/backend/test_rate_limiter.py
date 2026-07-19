"""Tests for the rate limiting middleware."""

from unittest.mock import patch


def test_rate_limiter_triggers_429(client):
    """Verify that when the rate limiter is exhausted, a 429 response is returned."""
    with patch("backend.core.rate_limiter.limiter.is_allowed", return_value=False):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "test", "input_type": "email"},
        )
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "Too Many Requests"
        assert "exceeded" in body["message"]


def test_rate_limiter_allows_under_limit(client):
    """Verify that when the rate limiter permits requests, the standard response logic flows (e.g. 401 unauthorized if token missing)."""
    with patch("backend.core.rate_limiter.limiter.is_allowed", return_value=True):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "test", "input_type": "email"},
        )
        # Should not be 429; it should pass to the endpoint/auth check and return 401
        assert resp.status_code == 401
