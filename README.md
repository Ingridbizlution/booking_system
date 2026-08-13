# Bizlution FMS — 會議室管理系統

依 Bizlution FMS 截圖實作的完整專案：**HTML + CSS 前端** ＋ **FastAPI + PostgreSQL 後端**。外觀以 [Tabler](https://tabler.io) 5（MIT License，公開 CDN）為底，Bizlution FMS 風格微調在 `assets/css/app.css`。

## 目前 vertical slice 範圍

- **M7 組織目錄**：用戶、群組、分支、樓層（完整 CRUD + JWT 認證）
- **M1 預約管理（限房間）**：房間 CRUD、預約建立/取消/審批/check-in、衝突判定、儀表板統計
- 其他模組頁面仍為靜態 UI，會在 launcher 上呈現「即將推出」

## 一鍵啟動

需要：Docker Desktop、Python 3（本機起前端 static server 用）

**步驟 1：啟動後端**

```bash
cd backend
docker compose up --build
```

首次啟動會自動：建 PostgreSQL → 建表 → 灌 seed 資料 → 啟 FastAPI 於 `http://localhost:8080`

**步驟 2：啟動前端（另開一個終端機）**

```bash
cd ..                # 回到專案根目錄
python3 -m http.server 8000
```

**步驟 3：開瀏覽器**

<http://localhost:8000> → 會自動導向登入頁

登入帳密：

| 角色 | 電子郵件 | 密碼 |
|---|---|---|
| Admin | `ingrid@bizlution.com` | `Ingrid1234!` |
| User | `ingridiaim@gmail.com` | `User1234!` |
| Staff | `m0341018@mail.hfu.edu.tw` | `Support1234!` |

登入後會進入 **啟動頁（launcher）**，點卡片進入對應模組。

## Demo 可以做的事

1. 登入 → 進啟動頁 → 點「預約管理」
2. 側欄「房間 / 標準房間」看 9 間會議室（從 PostgreSQL 撈）
3. 點房間名稱 → 開預約 modal → 建立預約（**有衝突判定**：試著在同時段再開一次會噴 409）
4. 返回「資訊主頁」→ 看 KPI 數字更新（資源、預約總數、總時數、使用率）
5. 進「組織目錄 / 用戶」→ 從 API 撈用戶清單，點「邀請」新增用戶
6. Swagger 文件：<http://localhost:8080/docs>

## 檔案結構

```
Bizlution FMS_part_frontend_v2/
  index.html                          # 進入頁（重導至 launcher）
  README.md                           # 本檔
  Bizlution FMS_規格書.docx                # 規格書
  assets/
    css/app.css                       # Bizlution FMS 風格 CSS
    js/app.js                         # 側欄 / 頂部列 / Modal 共通 JS
    js/api.js                         # API client（JWT + fetch 包裝）
  pages/
    launcher.html                     # 模組啟動頁（登入後首頁）
    login.html                        # 登入頁
    reservation-dashboard.html        # ★ 已接 API（儀表板統計）
    reservation-rooms.html            # ★ 已接 API（房間清單 + 預約 modal）
    reservation-team-spaces.html
    ticket-dashboard.html
    ticket-reports.html
    ticket-policies.html
    broadcast-announcements.html
    broadcast-emergency.html
    map.html
    signage-home.html
    signage-devices.html
    signage-playlists.html
    room-control.html
    org-users.html                    # ★ 已接 API（用戶清單 + 建立）
    org-groups.html
    org-branches.html
    system-audit.html
    system-email-templates.html
    media-library.html
  backend/                            # FastAPI + PostgreSQL
    Dockerfile
    docker-compose.yml
    requirements.txt
    README.md                         # 後端說明（含 API 對照、curl 範例）
    app/                              # 見 backend/README.md
```

## 常見問題

**Q. 前端載入卡在讀取中？**
確認 backend 有起（`docker compose ps`）且 `http://localhost:8080/health` 回 `{"status":"ok"}`。

**Q. CORS 錯誤？**
`backend/docker-compose.yml` 的 `CORS_ORIGINS` 需包含前端 URL。預設允許 `localhost:8000` / `127.0.0.1:8000`。

**Q. 想要清空資料重來？**
`cd backend && docker compose down -v && docker compose up --build`

**Q. 想直接查資料庫？**
`docker exec -it offision-db psql -U offision -d offision`

## 下一步（後續 slice 建議）

- **第二輪：** M2 工單管理 + M9 媒體庫（檔案上傳）
- **第三輪：** M3 廣播（含 WebSocket 即時推播）+ 審計 log 查詢介面
- **第四輪：** M4 地圖（樓層平面圖 + 圖釘座標）
- **第五輪：** M5 電子標牌（裝置心跳、離線同步、遠端截圖）
