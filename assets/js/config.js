/* Bizlution FMS 前端執行環境設定
 * ------------------------------------------------------------
 * 這個檔案裡的值會隨部署環境改變，其他 js 都不該寫死它們。
 * 載入順序：任何頁面都必須在 api.js **之前**引入本檔。
 *
 * 後端是 bizlution-fms-phase1-main 的 FMS Platform API（契約在該專案的
 * api/openapi.yaml，互動式瀏覽器在 <API 根>/docs）。
 */

/* API 根路徑。版本前綴 /api/v1 是契約固定的一部分，要一起帶。
 *
 * 本機開發：http://localhost:8080/api/v1
 * 線上：https://api.fms.bizlution.ai/api/v1 —— 但那台的 CORS 白名單目前
 *       只有 https://fms.bizlution.ai，從 localhost 開的前端會在 preflight
 *       就被擋掉（拿不到 Access-Control-Allow-Origin）。要改打線上，得先請
 *       後端把本站的來源加進 CORS_ALLOWED_ORIGINS。 */
window.OFF_API_BASE = window.OFF_API_BASE || 'http://localhost:8080/api/v1';

/* 租戶代碼。password grant 用它定位租戶（TokenRequest.tenant_code 必填）。
 *
 * 為什麼寫在設定裡而不是讓使用者在登入畫面輸入：fms.tenants 沒有 email
 * 網域欄位，因此無法從使用者輸入的 email 反推租戶；而單租戶部署下，要求
 * 使用者記住租戶代碼只是多一個會打錯的欄位。多租戶部署時再改成由子網域
 * 決定（例如 demo.fms.example.com → DEMO_GROUP）。 */
window.OFF_TENANT_CODE = window.OFF_TENANT_CODE || 'DEMO_GROUP';
