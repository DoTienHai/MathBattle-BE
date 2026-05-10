# 🔧 CORS & Network Debugging Notes

## 📅 May 8, 2026 - Register API Network Issue

### 🐛 Problem

```
ERROR: POST http://192.168.0.101:8000/api/v1/auth/register net::ERR_FAILED
Backend log: "OPTIONS /api/v1/auth/register HTTP/1.1" 400 Bad Request
```

### 🎯 Root Cause: CORS Preflight Failed

- React Native Metro (app port: `8081`) gửi POST request
- Browser/app tự động gửi **OPTIONS preflight** trước
- Backend trả `400 Bad Request` vì CORS không cấu hình cho origin này

---

## ✅ Solution: Fix Backend CORS Settings

### Backend CORS Config (Before - ❌ Wrong)

```python
# MathBattle-BE/settings/config.py
CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_METHODS: list = ["*"]
CORS_ALLOW_HEADERS: list = ["*"]
```

**Problem:** `192.168.0.101:8081` (app IP:port) không trong list!

### Backend CORS Config (After - ✅ Fixed)

```python
CORS_ORIGINS: list = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8081",
    "http://192.168.0.101:8081",  # ← React Native Metro bundler
]
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_METHODS: list = ["*"]
CORS_ALLOW_HEADERS: list = ["*"]
```

**Hoặc trong .env:**

```env
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://192.168.0.101:8081"]
```

### ⚠️ Important: Wildcard NOT Supported in Port

```python
# ❌ WRONG - Wildcard in port invalid
CORS_ORIGINS = ["http://192.168.0.101:*"]

# ✅ CORRECT - Exact match required
CORS_ORIGINS = ["http://192.168.0.101:8081"]
```

**Why?** CORS middleware does exact string matching:

- Request origin: `"http://192.168.0.101:8081"`
- List entry: `"http://192.168.0.101:*"` ≠ Match! ❌

---

## 🔍 How to Debug Network Errors

### Frontend Logging (Already Added)

```typescript
// app/services/api/client.ts

// Request interceptor logs:
[API REQUEST] 🚀 Starting request
  Method: POST
  URL: http://192.168.0.101:8000/api/v1/auth/register
  Base URL: http://192.168.0.101:8000
  Headers: {...}

// Error response logs:
[API ERROR] ❌ POST /api/v1/auth/register
  Error Code: ECONNREFUSED | ETIMEDOUT | ERR_FAILED
  Message: {...}
```

### Backend Logging Checklist

1. ✅ Backend running? `netstat -ano | findstr :8000` → LISTENING
2. ✅ Correct IP? `ipconfig` → IPv4 Address (Ethernet/WiFi adapter)
3. ✅ Firewall allow? Windows Defender → Allow python through firewall
4. ✅ Backend logs OPTIONS request? Yes = frontend reached backend

### Test Sequence

```
1. Frontend app sends POST request
   ↓
2. Browser/app auto-sends OPTIONS (preflight) first
   ↓
3. Backend receives OPTIONS request
   ↓
4. Backend checks CORS_ORIGINS match
   ↓
5. If match → Allow with 200 OK → Send actual POST
   If no match → Reject with 400 Bad Request → CORS Error
```

---

## 🚀 Steps to Fix

### Step 1: Update Backend CORS

File: `MathBattle-BE/app/settings/config.py` or `.env`

Add:

```python
"http://192.168.0.101:8081"  # React Native dev server
```

### Step 2: Restart Backend

```powershell
# Terminal running backend
Ctrl+C
uvicorn app.main:app --reload
# Should see: "INFO:     Application startup complete"
```

### Step 3: Test App Registration

- Frontend console should show:
  ```
  [API REQUEST] 🚀 Starting request
  [API SUCCESS] ✅ POST /api/v1/auth/register
    Status: 200
  ```

### Step 4: Verify Backend Log

```
INFO:     192.168.0.101:64064 - "OPTIONS /api/v1/auth/register HTTP/1.1" 200 OK
INFO:     192.168.0.101:64064 - "POST /api/v1/auth/register HTTP/1.1" 200 OK
```

---

## 📋 CORS Rules to Remember

| Origin                        | Allowed? | Reason               |
| ----------------------------- | -------- | -------------------- |
| `"*"`                         | ✅ Yes   | Allow all (DEV ONLY) |
| `"http://192.168.0.101:8081"` | ✅ Yes   | Exact match          |
| `"http://192.168.0.101:*"`    | ❌ No    | Wildcard not valid   |
| `"http://192.168.0.101"`      | ❌ No    | Port required        |
| `"localhost:8081"`            | ❌ No    | Protocol required    |

---

## 🎓 CORS Explained - Chi Tiết

### Đầu tiên: CORS là gì?

**CORS = Cross-Origin Resource Sharing**

Ngắn gọn: **Cho phép web/app từ domain này lấy dữ liệu từ domain kia**

```
Frontend: http://192.168.0.101:8081 (React Native app)
Backend:  http://192.168.0.101:8000 (API server)

Cùng IP nhưng khác PORT → Cần CORS!
```

---

### 🤔 Tại sao lại cần CORS?

**Vấn đề Security - Same-Origin Policy:**

```
❌ Browser/App mặc định BLOCK request giữa các origin khác nhau
   Tránh: Hacker lấy cắp dữ liệu từ Facebook, Gmail, v.v...

✅ CORS = Quy tắc cho phép an toàn
   Backend nói: "Được, tôi tin tưởng origin này"
   → Browser/App cho phép request đi
```

**Ví dụ:**

```
❌ Không CORS:
Frontend (port 8081) → Backend (port 8000)
Browser block → ERROR: CORS policy violation

✅ Có CORS:
Frontend (port 8081) → Backend (port 8000)
Backend: "OK, bạn là origin 8081, tôi cho phép"
Browser allow → ✅ Request OK
```

---

### 🔄 CORS Preflight Request - Cách hoạt động

**Khi frontend gửi POST/PUT/DELETE request:**

```
Step 1: Frontend gửi preflight request
┌─────────────────────────────────────────────┐
│ OPTIONS /api/v1/auth/register               │ ← Browser tự động gửi
│ Origin: http://192.168.0.101:8081           │ ← Origin là gì?
│ Access-Control-Request-Method: POST         │ ← Sắp gửi cái method gì?
│ Access-Control-Request-Headers: Content-Type│ ← Sắp dùng header nào?
└─────────────────────────────────────────────┘

Step 2: Backend kiểm tra CORS rules
Backend settings:
  CORS_ORIGINS = ["http://192.168.0.101:8081"]
  CORS_ALLOW_METHODS = ["*"]
  CORS_ALLOW_HEADERS = ["*"]

Questions:
  ✅ Origin "http://192.168.0.101:8081" trong CORS_ORIGINS? YES
  ✅ Method "POST" trong CORS_ALLOW_METHODS? YES (có "*")
  ✅ Headers được phép? YES (có "*")

Step 3: Backend trả response
┌──────────────────────────────────────────────┐
│ HTTP/1.1 200 OK                              │
│ Access-Control-Allow-Origin: http://192...   │
│ Access-Control-Allow-Methods: POST, GET, ... │
│ Access-Control-Allow-Headers: *              │
└──────────────────────────────────────────────┘

Step 4: Browser cho phép - gửi POST thực tế
┌──────────────────────────────────────────────┐
│ POST /api/v1/auth/register                   │
│ Content-Type: application/json               │
│ Origin: http://192.168.0.101:8081            │
│                                              │
│ {"email":"test@test.com", "password":"..."} │
└──────────────────────────────────────────────┘
```

---

### 🔴 CORS Error - Tại sao lỗi?

**Khi backend config CORS sai:**

```python
# ❌ WRONG Backend CORS Config
CORS_ORIGINS = ["http://localhost:3000"]

# App gửi request từ:
Origin: http://192.168.0.101:8081

# Backend check:
  http://192.168.0.101:8081 ≠ http://localhost:3000 ❌

# Backend response:
  HTTP/1.1 400 Bad Request
  ❌ No Access-Control-Allow-Origin header

# Browser block:
  ❌ CORS policy violation
  ❌ Request blocked
```

---

### ✅ CORS Settings - Mỗi cái làm gì?

```python
app.add_middleware(
    CORSMiddleware,

    # 1. CORS_ORIGINS - Danh sách origin được phép
    allow_origins=[
        "http://localhost:3000",        # ← localhost:3000 được
        "http://192.168.0.101:8081",    # ← IP:port này được
        "*"                              # ← Tất cả được (DEV ONLY!)
    ],

    # 2. CORS_ALLOW_CREDENTIALS - Cookie được gửi?
    allow_credentials=True,  # ← Cho phép gửi cookie/auth token

    # 3. CORS_ALLOW_METHODS - Những HTTP method nào được?
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # "*" = Tất cả method được

    # 4. CORS_ALLOW_HEADERS - Những headers nào được gửi?
    allow_headers=[
        "Content-Type",      # ← JSON headers
        "Authorization",     # ← Bearer token headers
        "Accept",
        "*"                  # ← Tất cả headers được
    ],
)
```

---

### 📊 CORS vs Non-CORS Request

```
=== Same-Origin (Không cần CORS) ===
Frontend: http://localhost:3000/app
Backend:  http://localhost:3000/api
→ Cùng domain, port → Browser cho phép, không preflight

=== Cross-Origin (Cần CORS) ===
Frontend: http://localhost:3000/app     (port 3000)
Backend:  http://localhost:8000/api     (port 8000)
→ Khác port → Browser cần CORS, gửi OPTIONS preflight

Frontend: http://192.168.0.101:8081/app  (IP:8081)
Backend:  http://192.168.0.101:8000/api  (IP:8000)
→ Khác port → Browser cần CORS, gửi OPTIONS preflight

Frontend: http://localhost/app
Backend:  http://192.168.0.101:8000/api
→ Khác IP → Browser cần CORS, gửi OPTIONS preflight
```

---

### 🧪 Test CORS Manuallly (Command Line)

```bash
# Test OPTIONS preflight
curl -X OPTIONS http://192.168.0.101:8000/api/v1/auth/register \
  -H "Origin: http://192.168.0.101:8081" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

# Check response headers:
# < Access-Control-Allow-Origin: http://192.168.0.101:8081 ✅
# < Access-Control-Allow-Methods: POST, OPTIONS, ... ✅
# < Access-Control-Allow-Headers: * ✅
```

---

### 🚨 Common CORS Errors & Solutions

| Error                                           | Nguyên nhân                                         | Giải pháp                             |
| ----------------------------------------------- | --------------------------------------------------- | ------------------------------------- |
| `CORS policy: No 'Access-Control-Allow-Origin'` | Backend không có CORS config                        | Thêm CORSMiddleware, set CORS_ORIGINS |
| `CORS policy: Origin not allowed`               | Origin không trong CORS_ORIGINS list                | Thêm origin vào list                  |
| `CORS policy: Method not allowed`               | HTTP method không trong CORS_ALLOW_METHODS          | Thêm method: `["POST", "GET", ...]`   |
| `CORS policy: Header not allowed`               | Header không trong CORS_ALLOW_HEADERS               | Thêm header hoặc set `["*"]`          |
| `CORS policy: credentials denied`               | CORS_ALLOW_CREDENTIALS = False nhưng app gửi cookie | Set `allow_credentials=True`          |

---

### 🎯 Best Practices

**Production:**

```python
# ✅ GOOD - Specific origins
CORS_ORIGINS = [
    "https://mathbattle.com",      # Domain production
    "https://app.mathbattle.com",  # App subdomain
    "https://www.mathbattle.com",
]

# ⚠️ BAD - Wildcard (unsafe)
CORS_ORIGINS = ["*"]  # Anyone can access!
```

**Development:**

```python
# ✅ OK - Multiple dev servers
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8081",
    "http://192.168.0.101:8081",
]

# ✅ ACCEPTABLE - For quick testing
CORS_ORIGINS = ["*"]  # Only in dev! Not production!
```

---

## 🎓 Frontend API Client Setup (Already Done)

### Logging in client.ts

- Request interceptor: Logs method, URL, headers, baseURL
- Response interceptor: Logs status, duration, full error details
- Network logger stores logs in AsyncStorage (max 50 logs)

### Debug Console Output

```
[API REQUEST] 🚀 Starting request
  Method: POST
  URL: http://192.168.0.101:8000/api/v1/auth/register
  Base URL: http://192.168.0.101:8000
  Full URL: http://192.168.0.101:8000/api/v1/auth/register
  Endpoint: /api/v1/auth/register

[API SUCCESS] ✅ POST /api/v1/auth/register
  Status: 200
  Duration: 245ms

// Or on error:
[API ERROR] ❌ POST /api/v1/auth/register
  Base URL: http://192.168.0.101:8000
  Full URL: http://192.168.0.101:8000/api/v1/auth/register
  Status: 400
  Error Code: ERR_BAD_REQUEST
  Message: ...
```

---

## 🔗 Related Files

- `app/services/authService.ts` - Register API call with logging
- `app/services/api/client.ts` - Axios client with interceptors
- `app/redux/thunks/authThunks.ts` - Register thunk dispatch
- `app/screens/auth/RegisterScreen.tsx` - UI form

---

**Status:** ✅ Fixed - CORS now properly configured
**Next:** Test register flow with fixed CORS settings
