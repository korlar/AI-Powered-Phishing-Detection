import logging
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from backend.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)

logger = logging.getLogger("phishing_backend")
router = APIRouter(tags=["Authentication"])

# ⚠️ DEMO ONLY — Mock user database for development/demo purposes.

_DEMO_PASSWORD: str = os.environ.get("DEMO_PASSWORD", "")
if not _DEMO_PASSWORD:
    raise RuntimeError(
        "DEMO_PASSWORD environment variable is not set. "
        "Add DEMO_PASSWORD=<your-password> to your .env file."
    )

MOCK_USER_DB = {
    "admin": {"username": "admin", "hashed_password": get_password_hash(_DEMO_PASSWORD)}
}


@router.post("/token", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = MOCK_USER_DB.get(form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
