import logging

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.core.config import EMAIL_THRESHOLD, MAX_BATCH_SIZE, URL_THRESHOLD

logger = logging.getLogger("phishing_backend")


class PhishingDetector:
    def __init__(self, model_path: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading RoBERTa model from '{model_path}' onto device: {self.device}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.model.to(self.device)
            # Ensure the model is set to evaluation mode (disables dropout/batchnorm updates)
            self.model.eval()
            self.status = "loaded"
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise e

    def predict(self, text: str) -> dict:
        # Tokenize the input text
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        )

        # Move tensors to the same device as the model
        inputs = {key: val.to(self.device) for key, val in inputs.items()}

        # Perform inference without tracking gradients to save memory
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.nn.functional.softmax(logits, dim=-1)

            # Handle both 2-class (URL) and 3-class (Email) models
            num_classes = probabilities.shape[-1]

            if num_classes == 3:
                # 0=Legitimate, 1=Spam, 2=Phishing
                phishing_confidence = probabilities[0][2].item()
                spam_confidence = probabilities[0][1].item()
                legitimate_confidence = probabilities[0][0].item()
                if phishing_confidence >= EMAIL_THRESHOLD:
                    is_phishing, message = True, "Phishing detected"
                    pred_confidence = phishing_confidence
                elif spam_confidence >= EMAIL_THRESHOLD:
                    is_phishing, message = False, "Spam detected"
                    pred_confidence = spam_confidence
                else:
                    is_phishing, message = False, "Content appears safe"
                    # Use certainty-of-safety score: how far the content is from any threat.
                    # Raw class-0 probability can be near 0 on borderline inputs, which
                    # looks misleading in the UI (e.g. "Safe — 1%").
                    pred_confidence = 1.0 - max(phishing_confidence, spam_confidence)
                class_scores = {
                    "phishing": round(phishing_confidence, 4),
                    "spam": round(spam_confidence, 4),
                    "legitimate": round(legitimate_confidence, 4),
                }
            else:
                # 0=Legitimate, 1=Phishing
                phishing_confidence = probabilities[0][1].item()
                legitimate_confidence = probabilities[0][0].item()
                is_phishing = bool(phishing_confidence >= URL_THRESHOLD)
                message = "Phishing detected" if is_phishing else "Content appears safe"
                pred_confidence = phishing_confidence if is_phishing else legitimate_confidence
                class_scores = {
                    "phishing": round(phishing_confidence, 4),
                    "legitimate": round(legitimate_confidence, 4),
                }

        return {
            "is_phishing": is_phishing,
            "confidence": round(pred_confidence, 4),
            "message": message,
            "class_scores": class_scores,
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        if not texts:
            return []

        results = []
        # Process in chunks to avoid GPU/CPU Out of Memory (OOM) errors
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch_texts = texts[i : i + MAX_BATCH_SIZE]

            inputs = self.tokenizer(
                batch_texts, return_tensors="pt", truncation=True, padding=True, max_length=512
            )

            inputs = {key: val.to(self.device) for key, val in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.nn.functional.softmax(logits, dim=-1)

            num_classes = probabilities.shape[-1]

            for prob in probabilities:
                if num_classes == 3:
                    phishing_confidence = prob[2].item()
                    spam_confidence = prob[1].item()
                    legitimate_confidence = prob[0].item()
                    if phishing_confidence >= EMAIL_THRESHOLD:
                        is_phishing, message = True, "Phishing detected"
                        pred_confidence = phishing_confidence
                    elif spam_confidence >= EMAIL_THRESHOLD:
                        is_phishing, message = False, "Spam detected"
                        pred_confidence = spam_confidence
                    else:
                        is_phishing, message = False, "Content appears safe"
                        # Same certainty-of-safety score as in predict().
                        pred_confidence = 1.0 - max(phishing_confidence, spam_confidence)
                    class_scores = {
                        "phishing": round(phishing_confidence, 4),
                        "spam": round(spam_confidence, 4),
                        "legitimate": round(legitimate_confidence, 4),
                    }
                else:
                    phishing_confidence = prob[1].item()
                    legitimate_confidence = prob[0].item()
                    is_phishing = bool(phishing_confidence >= URL_THRESHOLD)
                    message = "Phishing detected" if is_phishing else "Content appears safe"
                    pred_confidence = phishing_confidence if is_phishing else legitimate_confidence
                    class_scores = {
                        "phishing": round(phishing_confidence, 4),
                        "legitimate": round(legitimate_confidence, 4),
                    }

                results.append(
                    {
                        "is_phishing": is_phishing,
                        "confidence": round(pred_confidence, 4),
                        "message": message,
                        "class_scores": class_scores,
                    }
                )

        return results

    def explain(self, text: str, target_class: int | None = None) -> list[dict]:
        """
        Uses Gradient Norm (Saliency) to calculate the importance
        of each word toward the specified target class.
        """
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, padding=True, max_length=512
        )
        inputs = {key: val.to(self.device) for key, val in inputs.items()}

        # Access the embedding layer and require gradients
        embed_layer = self.model.get_input_embeddings()
        embeddings = embed_layer(inputs["input_ids"])
        embeddings.retain_grad()

        # Forward pass using inputs_embeds instead of input_ids
        outputs = self.model(inputs_embeds=embeddings, attention_mask=inputs["attention_mask"])
        logits = outputs.logits

        if target_class is None:
            target_class = int(torch.argmax(logits, dim=-1).item())

        self.model.zero_grad()
        logits[0, target_class].backward()

        # Compute Saliency (L2 norm of the gradients)
        importances = embeddings.grad[0].norm(dim=-1).detach().cpu().numpy()
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

        word_impacts = []
        for token, imp in zip(tokens, importances):
            if token not in self.tokenizer.all_special_tokens:
                clean_token = token.replace("Ġ", " ")
                word_impacts.append({"word": clean_token, "importance": float(imp)})

        return word_impacts
