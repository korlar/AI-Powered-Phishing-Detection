"""Tests for authentication endpoints and JWT token validation."""

from tests.conftest import DEMO_PASSWORD, DEMO_USERNAME


class TestLogin:
    """Tests for the /token endpoint."""

    def test_login_success(self, client):
        resp = client.post("/token", data={"username": DEMO_USERNAME, "password": DEMO_PASSWORD})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        resp = client.post("/token", data={"username": DEMO_USERNAME, "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/token", data={"username": "nobody", "password": DEMO_PASSWORD})
        assert resp.status_code == 401

    def test_login_empty_credentials(self, client):
        resp = client.post("/token", data={"username": "", "password": ""})
        assert resp.status_code == 422

    def test_login_missing_fields(self, client):
        resp = client.post("/token", data={})
        assert resp.status_code == 422


class TestAuthProtection:
    """Tests for JWT-protected endpoints."""

    def test_predict_without_token_is_rejected(self, client):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "test", "input_type": "email"},
        )
        assert resp.status_code == 401

    def test_predict_with_invalid_token_is_rejected(self, client):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "test", "input_type": "email"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_predict_with_malformed_auth_header(self, client):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "test", "input_type": "email"},
            headers={"Authorization": "NotBearer abc123"},
        )
        assert resp.status_code == 401

    def test_predict_with_valid_token_succeeds(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "Hello world", "input_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
