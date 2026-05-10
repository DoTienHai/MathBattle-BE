# Redux & API Integration Setup Guide

This document outlines the steps to complete the Redux and API integration for the MathBattle-FE app.

## 1. Install Required Dependencies

You need to install Redux Toolkit and React-Redux to the project:

```bash
cd d:\3_CODING\MathBattle\MathBattle-FE\app
npm install @reduxjs/toolkit react-redux axios
npm install --save-dev @types/react-redux
```

Or using yarn:

```bash
yarn add @reduxjs/toolkit react-redux axios
yarn add --dev @types/react-redux
```

## 2. Project Structure Overview

After setup, your Redux infrastructure will be organized as:

```
app/
├── redux/
│   ├── slices/           (Redux state slices)
│   │   └── authSlice.ts
│   ├── thunks/           (Async Redux actions)
│   │   └── authThunks.ts
│   ├── selectors/        (State selectors)
│   │   └── authSelectors.ts
│   └── store.ts          (Redux store config) ✅ READY
│
├── services/
│   ├── api/
│   │   └── client.ts     (Axios HTTP client) ✅ READY
│   └── authService.ts    (Auth API calls) ✅ READY
│
├── screens/auth/
│   └── LoginScreen.tsx   (Login UI + Redux) ✅ READY
│
├── types/
│   └── auth.ts           (TypeScript types) ✅ READY
│
├── providers.tsx         (Redux Provider wrapper) ✅ READY
├── .env                  (Environment config) ✅ READY
└── app/
    └── _layout.tsx       (Root layout - UPDATED with Providers) ✅ READY
```

## 3. Redux Architecture

### State Management Flow

```
User Action (Login Button)
    ↓
LoginScreen Component
    ↓
Dispatch loginUser thunk
    ↓
authService.login() → API call
    ↓
authSlice handles success/error
    ↓
Redux state updated
    ↓
useSelector hooks re-render component
    ↓
UI reflects new state
```

### Key Files

1. **authSlice.ts** - Redux state and reducers
   - Initial state with auth data
   - Sync actions: setLoading, setError, setUser, setTokens, etc.
   - Async thunks handlers (pending/fulfilled/rejected)

2. **authThunks.ts** - Async API operations
   - loginUser(email, password)
   - registerUser(email, password, fullName)
   - logoutUser()
   - getCurrentUser()
   - refreshAccessToken()
   - And more...

3. **authSelectors.ts** - State accessors
   - selectUser
   - selectToken
   - selectIsLoading
   - selectAuthError
   - selectIsAuthenticated
   - And more...

## 4. API Configuration

### Environment Variables

Edit `.env` to configure your backend API URL:

```env
# .env
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_ENV=development
```

**For Production:**

```env
EXPO_PUBLIC_API_URL=https://api.mathbattle.com
EXPO_PUBLIC_ENV=production
```

### API Client Features

The Axios client (`services/api/client.ts`) automatically:

- Adds Bearer token to all requests
- Handles 401 unauthorized errors
- Sets 30-second timeout
- Uses standard error format

### Authentication Flow

1. User enters email & password
2. LoginScreen dispatches `loginUser` thunk
3. authService calls `POST /api/v1/auth/login`
4. Backend returns: `{ access_token, refresh_token, user }`
5. Tokens saved to AsyncStorage
6. Redux state updated
7. Component redirects to home screen

## 5. Testing the Setup

### Step 1: Start the backend API

```bash
# From your backend project
cd d:\3_CODING\MathBattle\MathBattle-BE
python -m uvicorn main:app --reload --port 8000
```

Verify the backend is running:

- Open http://localhost:8000/docs
- You should see FastAPI Swagger documentation

### Step 2: Install dependencies

```bash
cd d:\3_CODING\MathBattle\MathBattle-FE\app
npm install
```

### Step 3: Start Expo

```bash
npm start
```

Then:

- Press `i` for iOS simulator
- Press `a` for Android emulator
- Press `w` for web browser

### Step 4: Test Login Flow

1. Navigate to Login tab
2. Enter test credentials:
   - Email: `test@example.com`
   - Password: `TestPassword123!` (or any password meeting the backend requirements)
3. Click "Log In"
4. Check:
   - Success message appears
   - Token is saved to AsyncStorage
   - Redux auth state is updated
   - User data is stored

### Step 5: Verify Token Storage

Open React Native Debugger and check AsyncStorage:

```
authToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 6. Redux DevTools (Optional)

To debug Redux in real-time, install Redux DevTools browser extension:

```bash
npm install --save-dev @reduxjs/redux-devtools
```

Then enable in store.ts:

```typescript
import { configureStore } from "@reduxjs/toolkit";
import { composeWithDevTools } from "@reduxjs/redux-devtools";

export const store = configureStore(
  {
    /* ... */
  },
  composeWithDevTools(),
);
```

## 7. API Response Format

All API responses follow this format:

```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "error": null
}
```

Or on error:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_PASSWORD",
    "message": "Invalid email or password"
  }
}
```

## 8. Backend Endpoints Reference

Based on `docs/01_Design/BE/USER_AUTH_DESIGN.md`:

| Method | Endpoint                | Body                         | Response                            |
| ------ | ----------------------- | ---------------------------- | ----------------------------------- |
| POST   | `/api/v1/auth/login`    | {email, password}            | {user, access_token, refresh_token} |
| POST   | `/api/v1/auth/register` | {email, password, full_name} | {user, access_token, refresh_token} |
| POST   | `/api/v1/auth/logout`   | -                            | {success}                           |
| GET    | `/api/v1/auth/me`       | -                            | {user}                              |
| POST   | `/api/v1/auth/refresh`  | -                            | {access_token}                      |

## 9. Next Steps (After Setup)

1. ✅ Redux store configured
2. ✅ API client ready
3. ✅ Login screen UI + Redux integration
4. 🔲 Test login flow against live API
5. 🔲 Implement navigation redirect after successful login
6. 🔲 Create auto-login on app startup
7. 🔲 Create RegisterScreen with `registerUser` thunk
8. 🔲 Create ForgotPasswordScreen
9. 🔲 Implement refresh token mechanism
10. 🔲 Add Remember me persistence to AsyncStorage

## 10. Common Issues & Solutions

### Issue: "Cannot find module 'react-redux'"

**Solution:** Run `npm install react-redux`

### Issue: "API request returns 401 Unauthorized"

**Solution:** Check that:

1. Backend is running (http://localhost:8000/docs)
2. Email is registered on backend
3. Password is correct
4. Token is saved correctly in AsyncStorage

### Issue: "Token saved but useSelector returns null"

**Solution:**

1. Verify authSlice is added to store.ts reducer config
2. Verify Providers component wraps root layout
3. Check Redux DevTools to see actual state

### Issue: "Password validation always fails"

**Solution:** Backend requires:

- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character

Example valid password: `Test@1234`

## 11. File Checklist

Before running the app, verify these files exist:

- ✅ `app/redux/store.ts`
- ✅ `app/redux/slices/authSlice.ts`
- ✅ `app/redux/thunks/authThunks.ts`
- ✅ `app/redux/selectors/authSelectors.ts`
- ✅ `app/services/api/client.ts`
- ✅ `app/services/authService.ts`
- ✅ `app/types/auth.ts`
- ✅ `app/screens/auth/LoginScreen.tsx`
- ✅ `app/providers.tsx`
- ✅ `app/.env`
- ✅ `app/app/_layout.tsx` (updated with Providers)

---

**Last Updated:** May 2026  
**Status:** Ready for testing  
**Next Action:** Run `npm install` and test login flow
