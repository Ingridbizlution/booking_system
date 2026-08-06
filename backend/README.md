# Offision Backend — Vertical Slice #1

**範圍：** M7 組織目錄（用戶 / 群組 / 分支 / 樓層）＋ M1 預約管理（限房間）

**技術：** FastAPI 0.115、SQLAlchemy 2、PostgreSQL 16、python-jose、Argon2、Docker Compose

## 一鍵啟動（推薦）

安裝好 Docker Desktop 後，於這個 `backend/` 資料夾執行：

```bash
docker compose up --build
```

首次啟動流程：

1. 啟動 PostgreSQL 16（映射到本機 `5433`）
2. 建立所有資料表（`app.db.init_db`）
3. 灌入示範資料（`app.seed`）
4. 啟動 FastAPI（`http://localhost:8080`）

啟動完成後：

- API 文件（Swagger）：<http://localhost:8080/docs>
- API 文件（ReDoc）：<http://localhost:8080/redoc>
- 健康檢查：<http://localhost:8080/health>

停止：`Ctrl + C`；清掉資料重來：`docker compose down -v`

## Demo 帳號

Seed 會自動建立三個帳號：

| 角色 | 電子郵件 | 密碼 |
|---|---|---|
| 系統管理員 | `ingrid@bizlution.com` | `Ingrid1234!` |
| 一般員工 | `ingridiaim@gmail.com` | `User1234!` |
| 支援職員 | `m0341018@mail.hfu.edu.tw` | `Support1234!` |

以及 3 個分支（HQ / 台北 / 新竹）、5 個樓層、9 間房間、1 筆示範預約。

## 主要 API

所有端點都在 `/api/v1` 之下。除 `/auth/login` 外皆需 `Authorization: Bearer <token>`。

- `POST /auth/login` — 登入
- `GET /users/me` — 取得自己
- `GET/POST /users` — 用戶清單 / 建立
- `PATCH /users/{id}` — 更新
- `GET/POST /groups` — 群組
- `POST /groups/{id}/members` — 加入成員
- `GET/POST /branches` — 分支機構
- `GET/POST /locations` — 樓層 / 建築
- `GET/POST /rooms` — 房間
- `PATCH/DELETE /rooms/{id}` — 更新 / 刪除
- `GET /reservations?resource_id=&from_at=&to_at=&status_filter=` — 預約清單
- `POST /reservations` — 建立（含衝突判定）
- `POST /reservations/{id}/approve` — 審批
- `POST /reservations/{id}/check-in` — 到場報到
- `DELETE /reservations/{id}` — 取消
- `GET /dashboard/reservation?from_date=&to_date=` — 儀表板統計

## 手動測試（curl）

```bash
# 1. 登入取得 token
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ingrid@bizlution.com","password":"Ingrid1234!"}' \
  | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# 2. 查所有房間
curl -s http://localhost:8080/api/v1/rooms -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 3. 儀表板
curl -s "http://localhost:8080/api/v1/dashboard/reservation?from_date=2026-08-01&to_date=2026-08-31" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 4. 建預約（會做衝突檢查）
curl -s -X POST http://localhost:8080/api/v1/reservations \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"resource_id":1,"title":"客戶會議","start_at":"2026-08-05T02:00:00Z","end_at":"2026-08-05T03:00:00Z"}'
```

## 專案結構

```
backend/
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
  app/
    main.py                  # FastAPI 入口
    core/
      config.py              # 環境變數
      security.py            # JWT + Argon2
    db/
      base.py                # Base + TimestampMixin
      session.py             # engine / SessionLocal / get_db
      init_db.py             # create_all（MVP 用）
    models/                  # SQLAlchemy models
      organization.py        # organizations / branches / locations
      user.py                # users / user_groups / user_group_members
      resource.py            # resources (type=room)
      reservation.py         # reservations / attendees
      audit.py               # audit_logs
    schemas/                 # Pydantic v2
    api/
      deps.py                # 目前使用者
      v1/
        auth.py
        users.py             # users + groups router
        branches.py          # branches + locations router
        rooms.py
        reservations.py
        dashboard.py
    seed.py                  # 示範資料
```

## 連接前端

前端目前接 `http://localhost:8080/api/v1`。CORS 已允許 `localhost:8000`（前端靜態 server 常用埠）。若你的前端跑在其他埠，修改 `docker-compose.yml` 的 `CORS_ORIGINS`。

前端流程：

1. 於 `frontend/pages/login.html` 登入 → token 存 `localStorage.off_token`
2. 進入 `launcher.html` → 顯示可用模組
3. 進入 `reservation-rooms.html`：從 `/rooms` 撈房間、點名稱可預約
4. 進入 `reservation-dashboard.html`：從 `/dashboard/reservation` 撈統計
5. 進入 `org-users.html`：從 `/users` 撈用戶、可新增

## 已知限制（第一輪）

- 尚未實作 refresh token、MFA、SSO
- 尚未實作邀請信寄送（`password` 空白時只是把 status 設為 pending）
- 尚未實作 recurrence rule 展開（RRULE parser）
- 尚未實作 reservation_rules（可預約時段、緩衝時間、每日上限等）
- 尚未實作預約審批工作流（MVP 直接 approved）
- 尚未實作圖片上傳與 QR 碼生成
- 尚未實作審計 log 查詢介面（有寫入，可 `docker exec` 查看）

這些會依序在後續 slice 補上。

## 從 create_all 遷移到 Alembic

正式環境請以 Alembic 管理 schema：

```bash
pip install alembic
alembic init alembic
# 編輯 alembic/env.py 使 target_metadata = Base.metadata
alembic revision --autogenerate -m "init"
alembic upgrade head
```
