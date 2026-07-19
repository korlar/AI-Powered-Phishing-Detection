from __future__ import annotations

from src.pipeline.aggregator import aggregate


def test_high_confidence_url_overrides_safe_email():
    """A highly confident phishing URL should override a completely safe-looking email body."""
    email_pred = {"is_phishing": False, "confidence": 0.99, "message": "Content appears safe"}
    url_preds = [
        {"is_phishing": False, "confidence": 0.99, "message": "Content appears safe"},
        {
            "is_phishing": True,
            "confidence": 0.85,
            "message": "Phishing detected",
        },  # High confidence malicious
    ]

    verdict = aggregate(email_pred, url_preds)

    assert verdict.is_phishing is True
    assert verdict.label == "Phishing"
    assert verdict.confidence == 0.85
    assert "High-confidence" in verdict.reason


def test_low_confidence_url_defers_to_email():
    """A low-confidence phishing URL (< 0.80) should defer to the email model's judgment."""
    email_pred = {"is_phishing": False, "confidence": 0.95, "message": "Content appears safe"}
    url_preds = [
        {"is_phishing": True, "confidence": 0.60, "message": "Phishing detected"}  # Low confidence
    ]

    verdict = aggregate(email_pred, url_preds)

    assert verdict.is_phishing is False
    assert verdict.label == "Legitimate"
    assert verdict.confidence == 0.95
    assert "Email body analysis" in verdict.reason


def test_email_spam_fallback():
    """If the email model detects spam, it should surface as 'Spam' (not Phishing or Legitimate)."""
    email_pred = {"is_phishing": False, "confidence": 0.90, "message": "Spam detected"}
    url_preds = [{"is_phishing": False, "confidence": 0.99, "message": "Content appears safe"}]

    verdict = aggregate(email_pred, url_preds)

    assert verdict.is_phishing is False
    assert verdict.label == "Spam"
    assert verdict.confidence == 0.90


def test_url_only_fallback():
    """If no email text is present, it should use the highest confidence URL."""
    email_pred = None
    url_preds = [{"is_phishing": True, "confidence": 0.75}]

    verdict = aggregate(email_pred, url_preds)

    assert verdict.is_phishing is True
    assert verdict.label == "Phishing"
    assert "URL analysis only" in verdict.reason
