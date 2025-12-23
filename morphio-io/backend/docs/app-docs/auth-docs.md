# Authentication Documentation

## Overview

The backend uses JWT (JSON Web Tokens) for authentication with CSRF protection for state-changing operations.

## Authentication Flow

1. **Login** (`POST /auth/login`)
   - Validates email/password
   - Returns access token (30 min) + refresh token (7 days)
   - Sets CSRF cookie

2. **Authenticated Requests**
   - Include `Authorization: Bearer <access_token>` header
   - For POST/PUT/DELETE: include `X-CSRF-Token` header

3. **Token Refresh** (`POST /auth/token/refresh`)
   - Send refresh token to get new access token
   - Old refresh token is blacklisted

4. **Logout** (`POST /auth/logout`)
   - Blacklists both tokens
   - Clears cookies

## JWT Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `JWT_SECRET_KEY` | - | Signing key (required in prod) |
| `JWT_ALGORITHM` | `HS256` | Algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

## CSRF Protection

CSRF tokens are required for state-changing requests (POST, PUT, DELETE).

- Cookie: `csrf_token` (HttpOnly=False, SameSite=Lax)
- Header: `X-CSRF-Token`
- Middleware: `app/middlewares/csrf.py`

Excluded paths: `/auth/login`, `/auth/register`, `/health/`

## Token Blacklisting

Revoked tokens are stored in Redis for the duration of their original TTL:
- `app/services/redis/blacklist.py`
- Checked on every authenticated request

## Security Middleware

### Security Headers (`app/middlewares/security.py`)

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: ...
Strict-Transport-Security: max-age=31536000
```

### Rate Limiting

- Redis-backed via slowapi
- Fallback to in-memory if Redis unavailable
- Configured per-route via `@rate_limit` decorator

## Related Files

- `app/routes/auth/` - Auth endpoints
- `app/services/security/` - Token handling, auth logic
- `app/middlewares/csrf.py` - CSRF middleware
- `app/middlewares/security.py` - Security headers