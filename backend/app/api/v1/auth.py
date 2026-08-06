"""登入 / token 端點。"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from ...db.session import get_db
from ...models import User
from ...core.security import verify_password, create_access_token
from ...core.config import settings
from ...schemas import LoginIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "電子郵件或密碼錯誤")
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "帳號未啟用")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=str(user.id), extra={"org": user.organization_id})
    return TokenOut(
        access_token=token,
        expires_in_min=settings.jwt_expires_min,
        user_id=user.id,
        organization_id=user.organization_id,
        display_name=user.display_name,
    )
