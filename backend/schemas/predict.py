from enum import Enum

from pydantic import BaseModel, Field, field_validator

from backend.core.config import MAX_BATCH_SIZE


class InputType(str, Enum):
    email = "email"
    url = "url"


class PredictRequest(BaseModel):
    text: str = Field(..., description="The text or URL to classify.")
    input_type: InputType = Field(..., description="The type of input: 'email' or 'url'.")
    explain: bool = Field(False, description="Whether to include word-level explanations.")


class PredictBatchRequest(BaseModel):
    texts: list[str] = Field(..., description="A list of texts or URLs to classify.")
    input_type: InputType = Field(..., description="The type of input: 'email' or 'url'.")

    @field_validator("texts")
    @classmethod
    def validate_batch_size(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("The list of texts must not be empty.")
        if len(v) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch size exceeds the maximum allowed limit of {MAX_BATCH_SIZE} items."
            )
        return v


class WordImportance(BaseModel):
    word: str
    importance: float


class PredictResponse(BaseModel):
    label: str = Field(
        ..., description="The predicted class label (e.g. Legitimate, Spam, Phishing)."
    )
    confidence: float = Field(..., description="The model confidence level.")
    is_phishing: bool = Field(..., description="Whether the content is classified as phishing.")
    message: str = Field(..., description="Details or reasoning for the prediction.")
    word_importances: list[WordImportance] | None = Field(
        None, description="Word-level importance explanations."
    )


class PredictBatchResponse(BaseModel):
    results: list[PredictResponse] = Field(..., description="A list of prediction results.")


class PredictionHistoryItem(BaseModel):
    id: int = Field(..., description="The unique ID of the log entry.")
    input_text: str = Field(..., description="The text or URL that was analyzed.")
    input_type: str = Field(..., description="The input type: 'email' or 'url'.")
    prediction_label: str = Field(..., description="The predicted classification label.")
    confidence: float = Field(..., description="The prediction confidence.")
    is_phishing: bool = Field(..., description="Whether the content was flagged as phishing.")
    reason: str = Field(..., description="The reasoning/message for the verdict.")
    timestamp: str = Field(..., description="The ISO/UTC timestamp of the check.")


class PredictionHistoryResponse(BaseModel):
    history: list[PredictionHistoryItem] = Field(..., description="A list of past prediction logs.")
