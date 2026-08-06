"""建立所有資料表（MVP 用；正式環境建議改用 Alembic）。"""
import time
from sqlalchemy.exc import OperationalError
from .base import Base
from .session import engine
from ..models import *  # noqa: F401,F403 讓 Base.metadata 認識所有 model


def init_db(retries: int = 30, delay_sec: float = 1.0):
    last_err = None
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("[init_db] tables ready")
            return
        except OperationalError as e:
            last_err = e
            print(f"[init_db] DB not ready ({i+1}/{retries}), retry in {delay_sec}s")
            time.sleep(delay_sec)
    raise RuntimeError(f"init_db failed: {last_err}")


if __name__ == "__main__":
    init_db()
