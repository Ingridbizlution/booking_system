"""建立所有資料表（MVP 用；正式環境建議改用 Alembic）。"""
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from .base import Base
from .session import engine
from ..models import *  # noqa: F401,F403 讓 Base.metadata 認識所有 model

#: create_all 只建立缺少的「表」，不會為既有表補「欄位」。
#: 新增欄位時在此登記，避免既有資料庫需要整個重建。
#: （正式環境請改用 Alembic；此處僅為 MVP 的權宜作法。）
ADD_COLUMNS = [
    ("assignable_roles", "key", "VARCHAR(60)"),
]


def _add_missing_columns():
    with engine.begin() as conn:
        for table, column, coltype in ADD_COLUMNS:
            exists = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :t AND column_name = :c
            """), {"t": table, "c": column}).scalar_one_or_none()
            if not exists:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN "{column}" {coltype}'))
                print(f"[init_db] 已新增欄位 {table}.{column}")


def init_db(retries: int = 30, delay_sec: float = 1.0):
    last_err = None
    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            _add_missing_columns()
            print("[init_db] tables ready")
            return
        except OperationalError as e:
            last_err = e
            print(f"[init_db] DB not ready ({i+1}/{retries}), retry in {delay_sec}s")
            time.sleep(delay_sec)
    raise RuntimeError(f"init_db failed: {last_err}")


if __name__ == "__main__":
    init_db()
