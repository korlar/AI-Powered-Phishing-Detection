import logging
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Request

from backend.core.config import KNOWN_SAFE_DOMAINS
from backend.core.database import clear_history, get_history, log_prediction
from backend.core.security import get_current_user
from backend.schemas.predict import (
    PredictBatchRequest,
    PredictBatchResponse,
    PredictionHistoryResponse,
    PredictRequest,
    PredictResponse,
)
from src.pipeline.aggregator import aggregate
from src.preprocess.email_parser import extract_urls
from src.preprocess.url_normalizer import normalize_url

logger = logging.getLogger("phishing_backend")

router = APIRouter(tags=["Prediction"])


@router.post("/api/v1/predict", response_model=PredictResponse)
async def predict_phishing(
    payload: PredictRequest, request: Request, current_user: dict = Depends(get_current_user)
):
    """Endpoint for RoBERTa phishing classification inference"""
    logger.info(
        f"Received prediction request from user '{current_user['username']}' (type={payload.input_type})",
        extra={"request_path": "/api/v1/predict"},
    )

    text_clean = payload.text.strip()

    if payload.input_type == "email":
        text_clean = text_clean.lower()
    ml_models = getattr(request.app.state, "ml_models", {})
    email_pred = None
    url_preds = []

    if payload.input_type == "url":
        # URL mode: treat the entire input as a URL
        if "url" in ml_models:
            normalized = normalize_url(text_clean)
            domain = urllib.parse.urlsplit(normalized).netloc.replace("www.", "")
            if domain in KNOWN_SAFE_DOMAINS:
                url_preds.append(
                    {
                        "is_phishing": False,
                        "confidence": 0.99,
                        "message": "Domain is in the verified safe allowlist.",
                    }
                )
            else:
                url_preds.append(ml_models["url"].predict(normalized))
    else:
        # Email mode: analyze as email body text
        if "email" in ml_models:
            email_pred = ml_models["email"].predict(text_clean)

        # Also check any embedded URLs in the email
        extracted_urls = extract_urls(text_clean)
        if "url" in ml_models:
            for u in extracted_urls:
                normalized = normalize_url(u)
                domain = urllib.parse.urlsplit(normalized).netloc.replace("www.", "")
                if domain in KNOWN_SAFE_DOMAINS:
                    url_preds.append(
                        {
                            "is_phishing": False,
                            "confidence": 0.99,
                            "message": "Domain is in the verified safe allowlist.",
                        }
                    )
                else:
                    url_preds.append(ml_models["url"].predict(normalized))

    verdict = aggregate(email_pred, url_preds)

    # Explainability is only available for email predictions
    if payload.explain and payload.input_type == "email" and "email" in ml_models:
        if verdict.label == "Phishing":
            target = 2
        elif verdict.label == "Spam":
            target = 1
        else:
            target = 0
        verdict.word_importances = ml_models["email"].explain(text_clean, target_class=target)

    # Log prediction to SQLite database
    log_prediction(
        input_text=text_clean,
        input_type=payload.input_type.value,
        prediction_label=verdict.label,
        confidence=verdict.confidence,
        is_phishing=verdict.is_phishing,
        reason=verdict.reason,
    )

    return verdict.dict()


@router.post("/api/v1/predict/batch", response_model=PredictBatchResponse)
async def predict_phishing_batch(
    payload: PredictBatchRequest, request: Request, current_user: dict = Depends(get_current_user)
):
    """Endpoint for batch RoBERTa phishing classification inference"""
    logger.info(
        f"Received batch prediction request for {len(payload.texts)} items (type={payload.input_type}) from user '{current_user['username']}'",
        extra={"request_path": "/api/v1/predict/batch"},
    )

    ml_models = getattr(request.app.state, "ml_models", {})
    results = []

    if payload.input_type == "url":
        # URL batch mode
        url_to_classify: list[tuple[int, str]] = []
        allowlist_results: dict[int, dict[str, Any]] = {}

        for i, text in enumerate(payload.texts):
            text_clean = text.strip()
            normalized = normalize_url(text_clean)
            domain = urllib.parse.urlsplit(normalized).netloc.replace("www.", "")
            if domain in KNOWN_SAFE_DOMAINS:
                allowlist_results[i] = {
                    "is_phishing": False,
                    "confidence": 0.99,
                    "message": "Domain is in the verified safe allowlist.",
                }
            else:
                url_to_classify.append((i, normalized))

        url_preds_raw = []
        if url_to_classify and "url" in ml_models:
            url_preds_raw = ml_models["url"].predict_batch([u[1] for u in url_to_classify])

        # Build index mapping for quick lookup
        url_inputs_map = {orig_i: idx for idx, (orig_i, _) in enumerate(url_to_classify)}

        for i in range(len(payload.texts)):
            if i in allowlist_results:
                verdict = aggregate(None, [allowlist_results[i]])
            else:
                idx = url_inputs_map[i]
                verdict = aggregate(None, [url_preds_raw[idx]])
            results.append(verdict.dict())

    else:
        # Email batch mode
        email_inputs: list[str] = []
        email_indices: list[int] = []
        url_map: dict[int, list[int]] = {i: [] for i in range(len(payload.texts))}
        url_preds_all: list[Any] = []
        email_extracted_urls: list[str] = []

        for i, text in enumerate(payload.texts):
            text_clean = text.strip()
            extracted = extract_urls(text_clean)

            if "url" in ml_models:
                for u in extracted:
                    normalized = normalize_url(u)
                    domain = urllib.parse.urlsplit(normalized).netloc.replace("www.", "")
                    if domain in KNOWN_SAFE_DOMAINS:
                        url_preds_all.append(
                            {
                                "is_phishing": False,
                                "confidence": 0.99,
                                "message": "Domain is in the verified safe allowlist.",
                            }
                        )
                    else:
                        email_extracted_urls.append(normalized)
                        url_preds_all.append(len(email_extracted_urls) - 1)
                    url_map[i].append(len(url_preds_all) - 1)

            if "email" in ml_models:
                email_inputs.append(text_clean.lower())
                email_indices.append(i)

        logger.info(
            f"Batch routing: {len(email_inputs)} to email model, {len(email_extracted_urls)} to url model."
        )

        email_preds_raw = []
        if email_inputs and "email" in ml_models:
            email_preds_raw = ml_models["email"].predict_batch(email_inputs)

        if email_extracted_urls and "url" in ml_models:
            url_preds_raw = ml_models["url"].predict_batch(email_extracted_urls)
            for j in range(len(url_preds_all)):
                if isinstance(url_preds_all[j], int):
                    url_preds_all[j] = url_preds_raw[url_preds_all[j]]

        email_indices_map = {orig_i: idx for idx, orig_i in enumerate(email_indices)}

        for i in range(len(payload.texts)):
            email_pred = None
            if i in email_indices_map:
                idx_in_email = email_indices_map[i]
                email_pred = email_preds_raw[idx_in_email]

            u_preds = [url_preds_all[u_idx] for u_idx in url_map[i]]

            verdict = aggregate(email_pred, u_preds)
            results.append(verdict.dict())

    # Log all batch predictions to SQLite database
    for i, text in enumerate(payload.texts):
        res = results[i]
        log_prediction(
            input_text=text.strip(),
            input_type=payload.input_type.value,
            prediction_label=res["label"],
            confidence=res["confidence"],
            is_phishing=res["is_phishing"],
            reason=res["message"],
        )

    return {"results": results}


@router.get("/api/v1/history", response_model=PredictionHistoryResponse)
async def get_prediction_history(current_user: dict = Depends(get_current_user)):
    """Retrieve recent prediction history log entries."""
    logger.info(
        f"User '{current_user['username']}' requested prediction history.",
        extra={"request_path": "/api/v1/history"},
    )
    history_logs = get_history()
    return {"history": history_logs}


@router.delete("/api/v1/history")
async def clear_prediction_history(current_user: dict = Depends(get_current_user)):
    """Clear all prediction history log entries."""
    logger.info(
        f"User '{current_user['username']}' requested clearing prediction history.",
        extra={"request_path": "/api/v1/history"},
    )
    success = clear_history()
    if success:
        return {"status": "success", "message": "Prediction history cleared."}
    else:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Failed to clear prediction history.")
