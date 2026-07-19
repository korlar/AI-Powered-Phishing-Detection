from unittest.mock import MagicMock, patch

import pytest
import torch

from backend.core.inference import PhishingDetector


class MockOutput:
    def __init__(self, logits):
        self.logits = logits


@pytest.fixture
def mock_transformers():
    with (
        patch("backend.core.inference.AutoTokenizer") as mock_tok,
        patch("backend.core.inference.AutoModelForSequenceClassification") as mock_model,
    ):
        # Setup mock tokenizer
        tokenizer_instance = MagicMock()
        tokenizer_instance.return_value = {
            "input_ids": torch.tensor([[0, 1, 2, 3, 4]]),
            "attention_mask": torch.tensor([[1, 1, 1, 1, 1]]),
        }
        tokenizer_instance.convert_ids_to_tokens.return_value = ["<s>", "hello", "Ġworld", "</s>"]
        tokenizer_instance.all_special_tokens = ["<s>", "</s>", "<pad>", "<unk>"]
        mock_tok.from_pretrained.return_value = tokenizer_instance

        # Setup mock model
        model_instance = MagicMock()
        mock_model.from_pretrained.return_value = model_instance

        yield tokenizer_instance, model_instance


def test_inference_initialization(mock_transformers):
    detector = PhishingDetector(model_path="dummy/path")
    assert detector.status == "loaded"


def test_inference_predict_email(mock_transformers):
    tokenizer, model = mock_transformers
    # 3 classes: Legitimate (0), Spam (1), Phishing (2)
    model.return_value = MockOutput(torch.tensor([[10.0, -10.0, -10.0]]))

    detector = PhishingDetector(model_path="dummy/path")
    result = detector.predict("hello world")
    assert result["is_phishing"] is False
    assert result["confidence"] > 0.90
    assert "safe" in result["message"].lower()


def test_inference_predict_url(mock_transformers):
    tokenizer, model = mock_transformers
    # 2 classes: Legitimate (0), Phishing (1)
    model.return_value = MockOutput(torch.tensor([[-5.0, 5.0]]))

    detector = PhishingDetector(model_path="dummy/path")
    result = detector.predict("http://test.com")
    assert result["is_phishing"] is True
    assert result["confidence"] > 0.90
    assert "phishing" in result["message"].lower()


def test_inference_predict_batch(mock_transformers):
    tokenizer, model = mock_transformers
    # Mocking two items in the batch returning 3 classes each
    model.return_value = MockOutput(torch.tensor([[10.0, -10.0, -10.0], [10.0, -10.0, -10.0]]))

    detector = PhishingDetector(model_path="dummy/path")
    results = detector.predict_batch(["test 1", "test 2"])
    assert len(results) == 2
    assert results[0]["is_phishing"] is False


def test_inference_explain(mock_transformers):
    tokenizer, model = mock_transformers
    detector = PhishingDetector(model_path="dummy/path")

    # Setup mock embedding layer that returns a tensor with requires_grad=True
    mock_embeddings = torch.randn(1, 5, 768, requires_grad=True)

    mock_embed_layer = MagicMock()
    mock_embed_layer.return_value = mock_embeddings
    model.get_input_embeddings.return_value = mock_embed_layer

    # Return logits computed from inputs_embeds so gradient tracking works
    def side_effect_forward(inputs_embeds, attention_mask=None):
        logits = inputs_embeds.sum(dim=-1)[:, :3]
        return MockOutput(logits)

    model.side_effect = side_effect_forward

    explanations = detector.explain("hello world")
    assert len(explanations) == 2  # "hello", "Ġworld"
    assert "word" in explanations[0]
    assert "importance" in explanations[0]
    assert isinstance(explanations[0]["importance"], float)
