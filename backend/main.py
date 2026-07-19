import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.auth import router as auth_router
from backend.api.predict import router as predict_router
from backend.core.config import ALLOWED_ORIGINS, EMAIL_MODEL_PATH, URL_MODEL_PATH
from backend.core.database import init_db
from backend.core.inference import PhishingDetector
from backend.core.rate_limiter import RateLimitingMiddleware


# --- Structured JSON Logging Setup ---
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if hasattr(record, "request_path"):
            log_record["request_path"] = record.request_path
        if hasattr(record, "execution_time"):
            log_record["execution_time"] = record.execution_time
        if hasattr(record, "status_code"):
            log_record["status_code"] = record.status_code
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


logger = logging.getLogger("phishing_backend")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)


def load_roberta_models():
    """
    Function to load the local RoBERTa models and tokenizers.
    """
    logger.info("Initializing RoBERTa model inference pipelines...")
    email_path = EMAIL_MODEL_PATH
    url_path = URL_MODEL_PATH

    models = {}
    try:
        models["email"] = PhishingDetector(model_path=email_path)
    except Exception as e:
        logger.error(f"Failed to load Email model from {email_path}: {e}")

    try:
        models["url"] = PhishingDetector(model_path=url_path)
    except Exception as e:
        logger.error(f"Failed to load URL model from {url_path}: {e}")

    return models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database and load models
    init_db()
    try:
        app.state.ml_models = load_roberta_models()
        logger.info("Machine learning models successfully loaded into memory.")
    except Exception as e:
        logger.error(f"Failed to load machine learning models: {e}", exc_info=True)
        app.state.ml_models = {}

    yield

    # Shutdown: Clean up resources to prevent memory leaks
    if hasattr(app.state, "ml_models"):
        app.state.ml_models.clear()
    logger.info("Machine learning models unloaded.")


# --- FastAPI Initialization ---
app = FastAPI(
    title="Phishing Detection API",
    description="Backend API for the AI-Powered Phishing Detection System",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Register Routers ---
app.include_router(auth_router)
app.include_router(predict_router)

# --- Config ---
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5 MB payload size limit

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Configured via ALLOWED_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitingMiddleware)

# Compress responses larger than 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def enforce_payload_size_limit(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_BYTES:
        logger.warning(
            f"Rejected request: Payload size ({content_length} bytes) exceeds limit",
            extra={"request_path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": "Payload Too Large",
                "message": f"Payload exceeds the maximum allowed size of {MAX_PAYLOAD_BYTES / 1024 / 1024:.0f}MB.",
            },
        )
    return await call_next(request)


@app.middleware("http")
async def log_requests_and_timing(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"Handled request {request.method} {request.url.path}",
        extra={
            "request_path": request.url.path,
            "execution_time": round(process_time, 4),
            "status_code": response.status_code,
        },
    )
    return response


# --- Global Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Validation error on payload", extra={"request_path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation Error", "details": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP error triggered: {exc.detail}", extra={"request_path": request.url.path})
    return JSONResponse(
        status_code=exc.status_code, content={"error": "HTTP Error", "message": exc.detail}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled system exception: {exc}",
        exc_info=True,
        extra={"request_path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred during processing.",
        },
    )


# --- Health Route ---
@app.get("/health")
async def health_check(request: Request):
    ml_models = getattr(request.app.state, "ml_models", {})

    email_meta = {}
    email_meta_path = os.path.join(EMAIL_MODEL_PATH, "metadata.json")
    if os.path.exists(email_meta_path):
        try:
            with open(email_meta_path) as f:
                email_meta = json.load(f)
        except Exception:
            pass

    url_meta = {}
    url_meta_path = os.path.join(URL_MODEL_PATH, "metadata.json")
    if os.path.exists(url_meta_path):
        try:
            with open(url_meta_path) as f:
                url_meta = json.load(f)
        except Exception:
            pass

    return {
        "status": "healthy",
        "email_model": {
            "status": "loaded" if "email" in ml_models else "unloaded",
            "metadata": email_meta,
        },
        "url_model": {
            "status": "loaded" if "url" in ml_models else "unloaded",
            "metadata": url_meta,
        },
    }
