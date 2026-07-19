"""Tests for prediction endpoints — single and batch, email and URL modes."""


class TestSinglePredictEmail:
    """Tests for POST /api/v1/predict with input_type='email'."""

    def test_safe_email_returns_not_phishing(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "Hello, this is a normal email.", "input_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_phishing"] is False
        assert 0.0 <= body["confidence"] <= 1.0
        assert "message" in body

    def test_phishing_email_returns_phishing(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "Click here to verify your fake-bank account!", "input_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_phishing"] is True

    def test_email_with_explain_returns_word_importances(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={
                "text": "Urgent: verify your fake-bank account immediately",
                "input_type": "email",
                "explain": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("word_importances") is not None
        assert len(body["word_importances"]) > 0
        assert "word" in body["word_importances"][0]
        assert "importance" in body["word_importances"][0]

    def test_email_without_explain_has_no_word_importances(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "Hello world", "input_type": "email", "explain": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("word_importances") is None

    def test_empty_text_still_returns_200(self, client, auth_headers):
        """Empty text is valid input — the model should handle it gracefully."""
        resp = client.post(
            "/api/v1/predict",
            json={"text": "   ", "input_type": "email"},
            headers=auth_headers,
        )
        # The API should not crash on whitespace-only input
        assert resp.status_code == 200


class TestSinglePredictUrl:
    """Tests for POST /api/v1/predict with input_type='url'."""

    def test_safe_url_returns_not_phishing(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "https://example.com", "input_type": "url"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "is_phishing" in body
        assert "confidence" in body

    def test_allowlisted_domain_is_safe(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "https://google.com/search?q=test", "input_type": "url"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_phishing"] is False
        assert body["confidence"] == 0.99
        assert "allowlist" in body["message"].lower()

    def test_phishing_url_is_detected(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "https://fake-bank.evil.com/login", "input_type": "url"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_phishing"] is True


class TestBatchPredict:
    """Tests for POST /api/v1/predict/batch."""

    def test_email_batch_returns_correct_count(self, client, auth_headers):
        texts = ["Hello world", "This is a fake-bank alert", "Normal message"]
        resp = client.post(
            "/api/v1/predict/batch",
            json={"texts": texts, "input_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 3

    def test_url_batch_returns_correct_count(self, client, auth_headers):
        texts = ["https://google.com", "https://fake-bank.com", "https://example.org"]
        resp = client.post(
            "/api/v1/predict/batch",
            json={"texts": texts, "input_type": "url"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 3

    def test_batch_with_allowlisted_url(self, client, auth_headers):
        texts = ["https://google.com", "https://suspicious-site.xyz"]
        resp = client.post(
            "/api/v1/predict/batch",
            json={"texts": texts, "input_type": "url"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        # Google should be safe via allowlist
        assert results[0]["is_phishing"] is False
        assert results[0]["confidence"] == 0.99

    def test_batch_without_auth_is_rejected(self, client):
        resp = client.post(
            "/api/v1/predict/batch",
            json={"texts": ["test"], "input_type": "email"},
        )
        assert resp.status_code == 401


class TestValidation:
    """Tests for request validation."""

    def test_missing_text_field(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"input_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_input_type(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "Hello"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_invalid_input_type(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict",
            json={"text": "Hello", "input_type": "sms"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_batch_missing_texts(self, client, auth_headers):
        resp = client.post(
            "/api/v1/predict/batch",
            json={"input_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestHealthCheck:
    """Tests for the /health endpoint."""

    def test_health_returns_model_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "email_model" in body
        assert "url_model" in body
