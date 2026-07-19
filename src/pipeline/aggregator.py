from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.core.config import URL_PHISHING_OVERRIDE_THRESHOLD


@dataclass
class UnifiedVerdict:
    label: str
    confidence: float
    is_phishing: bool
    reason: str
    word_importances: list[dict[str, Any]] | None = None

    def dict(self) -> dict[str, Any]:
        """Converts the verdict into a dictionary for the FastAPI JSON response."""
        return {
            "label": self.label,
            "confidence": self.confidence,
            "is_phishing": self.is_phishing,
            "message": self.reason,
            "word_importances": self.word_importances,
        }


def aggregate(email_pred: dict[str, Any] | None, url_preds: list[dict[str, Any]]) -> UnifiedVerdict:
    """
    Aggregates predictions from the email model and extracted URLs
    into a single unified verdict based on security precedence rules.
    """
    # 1. High-confidence malicious URL override (Highest priority signal)
    for upred in url_preds:
        if (
            upred.get("is_phishing")
            and upred.get("confidence", 0.0) >= URL_PHISHING_OVERRIDE_THRESHOLD
        ):
            class_scores = upred.get("class_scores", {})
            if class_scores:
                score_parts = []
                for cls_name in ("phishing", "legitimate"):
                    if cls_name in class_scores:
                        score_parts.append(
                            f"{cls_name.capitalize()}: {class_scores[cls_name] * 100:.2f}%"
                        )
                url_override_reason = (
                    f"High-confidence phishing URL detected — {', '.join(score_parts)}"
                )
            else:
                url_override_reason = "High-confidence phishing URL detected in content."
            return UnifiedVerdict(
                label="Phishing",
                confidence=upred["confidence"],
                is_phishing=True,
                reason=url_override_reason,
            )

    # 2. Email model fallback
    if email_pred:
        # Derive the label from class_scores (same source of truth as inference.py),
        # falling back to is_phishing / message only if class_scores is absent.
        class_scores = email_pred.get("class_scores", {})
        if class_scores:
            phishing_score = class_scores.get("phishing", 0.0)
            spam_score = class_scores.get("spam", 0.0)
            legitimate_score = class_scores.get("legitimate", 0.0)
            winning_score = max(phishing_score, spam_score, legitimate_score)
            if winning_score == phishing_score:
                label = "Phishing"
            elif winning_score == spam_score:
                label = "Spam"
            else:
                label = "Legitimate"

            score_parts = [
                f"{cls.capitalize()}: {class_scores[cls] * 100:.2f}%"
                for cls in ("phishing", "spam", "legitimate")
                if cls in class_scores
            ]
            reason = f"Email analysis — {', '.join(score_parts)}"
        else:
            # Fallback: no class_scores available (e.g. URL-only path)
            msg = email_pred.get("message", "").lower()
            if email_pred.get("is_phishing"):
                label = "Phishing"
            elif "spam" in msg:
                label = "Spam"
            else:
                label = "Legitimate"
            reason = f"Email body analysis: {label}"

        return UnifiedVerdict(
            label=label,
            confidence=email_pred.get("confidence", 0.0),
            is_phishing=label == "Phishing",
            reason=reason,
        )

    # 3. URL-only fallback (No email body, and URLs were either safe or low-confidence)
    if url_preds:
        highest_url = max(url_preds, key=lambda x: x.get("confidence", 0.0))
        is_phish = highest_url.get("is_phishing", False)
        class_scores = highest_url.get("class_scores", {})
        if class_scores:
            score_parts = []
            for cls_name in ("phishing", "legitimate"):
                if cls_name in class_scores:
                    score_parts.append(
                        f"{cls_name.capitalize()}: {class_scores[cls_name] * 100:.2f}%"
                    )
            url_reason = f"URL analysis \u2014 {', '.join(score_parts)}"
        else:
            url_reason = highest_url.get("message", "URL analysis only.")
        return UnifiedVerdict(
            label="Phishing" if is_phish else "Legitimate",
            confidence=highest_url.get("confidence", 0.0),
            is_phishing=is_phish,
            reason=url_reason,
        )

    # 4. Unknown fallback (No valid text or URLs provided)
    return UnifiedVerdict(
        label="Unknown",
        confidence=0.0,
        is_phishing=False,
        reason="No valid text or URLs provided to analyze.",
        word_importances=None,
    )
