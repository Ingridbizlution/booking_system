"""FastAPI 依賴注入：DB session、目前登入使用者、授權守衛。"""
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..core.rbac import has_permission, is_admin_user, is_super_admin
from ..core.security import decode_token
from ..db.session import get_db
from ..models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    user_id = int(payload.get("sub", 0))
    user = db.get(User, user_id)
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")
    return user


def get_current_tenant(user: User = Depends(get_current_user)) -> int:
    return user.organization_id


# ---------------- 授權守衛 ----------------

def require_permission(module: str, action: str = "write") -> Callable[..., User]:
    """產生一個要求 ``module:action`` 權限的依賴。

    用法::

        @router.post("", dependencies=[Depends(require_permission("resource"))])

    或需要取得使用者時::

        user: User = Depends(require_permission("resource"))
    """

    def dependency(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(db, user, module, action):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"需要 {module}:{action} 權限",
            )
        return user

    return dependency


def require_admin(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    """要求組織全域管理員。"""
    if not is_admin_user(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理員權限")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """要求 super admin（例如授予 / 撤銷 super admin 本身）。"""
    if not is_super_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要 super admin 權限")
    return user
