import pytest
from pydantic import ValidationError

from backend.schemas.predict import (
    InputType,
    PredictBatchRequest,
    PredictionHistoryItem,
    PredictRequest,
    PredictResponse,
)


def test_predict_request_validation():
    # Valid email input
    req = PredictRequest(text="Check this email", input_type="email", explain=True)
    assert req.text == "Check this email"
    assert req.input_type == InputType.email
    assert req.explain is True

    # Valid url input
    req_url = PredictRequest(text="https://google.com", input_type="url")
    assert req_url.input_type == InputType.url
    assert req_url.explain is False

    # Invalid input_type
    with pytest.raises(ValidationError):
        PredictRequest(text="hello", input_type="invalid_type")

    # Missing required field
    with pytest.raises(ValidationError):
        PredictRequest(input_type="email")


def test_predict_batch_request_validation():
    # Valid batch
    req = PredictBatchRequest(texts=["hi", "there"], input_type="email")
    assert req.texts == ["hi", "there"]
    assert req.input_type == InputType.email

    # Empty batch list (should fail via field_validator)
    with pytest.raises(ValidationError):
        PredictBatchRequest(texts=[], input_type="email")

    # Too large batch (should fail via field_validator when exceeding MAX_BATCH_SIZE)
    # MAX_BATCH_SIZE is default 32
    with pytest.raises(ValidationError):
        PredictBatchRequest(texts=["url"] * 33, input_type="url")


def test_predict_response_validation():
    # Valid response
    resp = PredictResponse(
        label="Legitimate",
        confidence=0.995,
        is_phishing=False,
        message="Safe link.",
        word_importances=[{"word": "safe", "importance": 0.1}],
    )
    assert resp.label == "Legitimate"
    assert resp.confidence == 0.995
    assert resp.is_phishing is False
    assert len(resp.word_importances) == 1
    assert resp.word_importances[0].word == "safe"


def test_prediction_history_item_validation():
    # Valid item
    item = PredictionHistoryItem(
        id=1,
        input_text="http://fake.com",
        input_type="url",
        prediction_label="Phishing",
        confidence=0.88,
        is_phishing=True,
        reason="Detected phishing",
        timestamp="2026-07-06 16:51:17",
    )
    assert item.id == 1
    assert item.is_phishing is True
