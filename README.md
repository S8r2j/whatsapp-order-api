# WhatsApp Order API

> **FastAPI backend for a multi-tenant WhatsApp Order Management platform.**
>
> Shop owners connect their WhatsApp Business Account via Meta OAuth. Customers send orders over WhatsApp; those messages are automatically parsed, structured, and stored. Shop staff manage orders, update statuses, and reply to customers — all through the companion dashboard.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Security & Privacy](#security--privacy)
- [Quick Start (Docker)](#quick-start-docker)
- [Manual Setup](#manual-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [WhatsApp Setup](#whatsapp-setup)
- [Database Migrations](#database-migrations)
- [Background Tasks](#background-tasks)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Overview

This service is the backend half of the WhatsApp Order Management system. It:

1. **Receives webhooks** from Meta's WhatsApp Cloud API when customers send messages.
2. **Parses free-text order messages** into structured records (items, quantity, total).
3. **Routes messages to the correct shop** in a multi-tenant setup using the phone number ID.
4. **Sends WhatsApp notifications** back to customers when order status changes (confirmed, ready, delivered, cancelled).
5. **Exposes a REST API** consumed by the React dashboard for order, customer, and shop management.
6. **Runs background tasks** via Celery: daily summaries, token refresh, and old-message cleanup.

---

## Architecture

```
Customer (WhatsApp)
    │
    ▼
Meta Cloud API  ─────────────────────────────────────────────────────┐
    │                                                                 │
    │  POST /webhook  (inbound messages)                              │  GET /webhook (verification)
    ▼                                                                 │
WhatsApp Order API  ◄────────────────────────────────────────────────┘
    │
    ├── Parse order text → OrderParser
    ├── Lookup shop by phone_number_id (SocialConnection)
    ├── Create / update Customer, Order, Message records
    ├── Encrypt sensitive fields (Fernet)
    ├── Store in PostgreSQL
    └── Send auto-reply via Meta Cloud API
    │
    ▼
React Dashboard  ─── GET/PATCH /api/v1/orders, /customers, /shop …
    │
    └── Shop updates order status → API sends WhatsApp template notification
```

**Multi-tenancy:** Every shop is a separate tenant. `SocialConnection` maps a Meta phone number ID to a shop and stores the OAuth access token (encrypted). All data (orders, customers, messages) is scoped by `shop_id`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | **FastAPI 0.111** (async, OpenAPI auto-docs) |
| Server | **Uvicorn 0.29** (ASGI) |
| Database | **PostgreSQL 16** (via Docker) |
| ORM | **SQLAlchemy 2.0** (async + `asyncpg` driver) |
| Migrations | **Alembic 1.13** |
| Validation | **Pydantic v2** + **pydantic-settings** |
| Auth | **python-jose** (JWT) · **bcrypt** (password hashing) |
| Encryption | **cryptography** (Fernet symmetric encryption) |
| Task Queue | **Celery 5.4** + **Redis 7** (broker + result backend) |
| HTTP Client | **httpx 0.27** (async, used for Meta API calls) |
| Rate Limiting | **slowapi 0.1.9** |
| Logging | **structlog 24.2** (structured JSON logs) |
| Monitoring | **sentry-sdk 2.2** (optional) |
| Testing | **pytest 8.2** · **pytest-asyncio** · **faker** |
| Linting | **ruff** · **mypy** (strict) |

---

## Features

### Order Lifecycle
- Statuses: `new` → `confirmed` → `ready` → `delivered` | `cancelled`
- Auto-parsed from free-text WhatsApp messages
- WhatsApp template notification sent on every status change
- Manual reply support from the dashboard

### Multi-Tenant Architecture
- Each shop is an isolated tenant with its own customers, orders, and messages
- Meta OAuth 2.0 flow — shops connect their own WhatsApp Business Account
- Webhook routes inbound messages by `phone_number_id` to the correct shop
- Access tokens stored encrypted and auto-refreshed before expiry (Celery task)

### Customer Management
- Customers created automatically on first message
- SHA-256 hash index on phone for fast lookups without decrypting
- Full order history per customer

### Conversation Threading
- Every inbound and outbound message stored with direction flag
- Linked to orders for full context

### Background Tasks (Celery + Redis)
| Task | Schedule | Description |
|------|----------|-------------|
| `send_daily_summaries` | 8 PM UTC daily | Order count summary to each shop owner |
| `cleanup_old_messages` | 2 AM UTC every Sunday | Delete messages older than 90 days |
| Token refresh | On demand | Re-fetch Meta OAuth token before expiry |

### Security
- Field-level Fernet encryption for all PII at rest (see table below)
- SHA-256 hash indexes for fast encrypted lookups
- JWT auth on all dashboard endpoints (7-day expiry, configurable)
- bcrypt password hashing
- Rate limiting on `/auth/login` and `/auth/register`
- Non-root user inside Docker container
- `Request-ID` middleware for distributed tracing
- CORS restricted to configured origins

---

## Security & Privacy

All sensitive fields are **encrypted at rest** using Fernet symmetric encryption before writing to PostgreSQL. The encryption key never leaves your server.

| Table | Field | Encrypted |
|-------|-------|:---------:|
| `shops` | `name`, `email`, `phone_number` | ✅ |
| `customers` | `phone_number` | ✅ |
| `orders` | `raw_message`, `notes` | ✅ |
| `messages` | `body` | ✅ |
| `social_connections` | `access_token`, `refresh_token` | ✅ |

**Hash lookups:** `email_hash` and `phone_hash` (SHA-256, one-way) are stored alongside encrypted values for O(1) equality lookups without decryption.

> **Important:** Rotate `ENCRYPTION_KEY` and re-encrypt data if it is ever exposed. The key is the only thing standing between the ciphertext and the plaintext.

---

## Quick Start (Docker)

The fastest way to get everything running locally.

**Prerequisites:** Docker + Docker Compose

```bash
# 1. Clone the repo
git clone https://github.com/S8r2j/whatsapp-order-api.git
cd whatsapp-order-api

# 2. Copy and fill in the environment file
cp .env.example .env

# 3. Generate a Fernet encryption key
python scripts/generate_encryption_key.py
# → Paste the output as ENCRYPTION_KEY in .env

# 4. Generate a JWT secret
openssl rand -hex 32
# → Paste the output as JWT_SECRET_KEY in .env

# 5. Fill in Meta credentials (see WhatsApp Setup section)
#    META_APP_ID, META_APP_SECRET, WEBHOOK_VERIFY_TOKEN

# 6. Start all services (PostgreSQL, Redis, API, Celery worker + beat)
docker-compose up --build

# 7. Apply database migrations (first time only)
docker-compose exec api alembic upgrade head
```

Services started by Docker Compose:

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5432 | PostgreSQL 16 database |
| `redis` | 6379 | Redis 7 (broker + cache) |
| `api` | 8000 | FastAPI application |
| `celery_worker` | — | Async task processor |
| `celery_beat` | — | Task scheduler |

**API is live at:** `http://localhost:8000`
**Interactive docs:** `http://localhost:8000/docs`

---

## Manual Setup

For development without Docker.

**Prerequisites:** Python 3.11+, PostgreSQL, Redis

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL to your local Postgres, fill in secrets

# 4. Apply migrations
alembic upgrade head

# 5. Start the API (hot reload)
uvicorn app.main:app --reload --port 8000

# 6. Start Celery worker (new terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# 7. Start Celery beat scheduler (new terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in all required values. **Never commit `.env`.**

| Variable | Required | Description |
|----------|:--------:|-------------|
| `ENVIRONMENT` | ☐ | `development` or `production` (default: `development`) |
| `APP_NAME` | ☐ | Display name for the application |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host:5432/db` |
| `ENCRYPTION_KEY` | ✅ | Fernet key — run `python scripts/generate_encryption_key.py` |
| `JWT_SECRET_KEY` | ✅ | 64-char random hex — run `openssl rand -hex 32` |
| `JWT_ALGORITHM` | ☐ | `HS256` (default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ☐ | Token TTL in minutes (default: `10080` = 7 days) |
| `META_APP_ID` | ✅ | Meta Developers dashboard → your Business App ID |
| `META_APP_SECRET` | ✅ | Meta App Secret (used for OAuth token exchange) |
| `FRONTEND_URL` | ✅ | Dashboard URL (e.g. `http://localhost:3000`) |
| `BACKEND_URL` | ✅ | This API's public URL (used for OAuth redirect) |
| `WHATSAPP_TOKEN` | ☐ | Legacy fallback token (usually set per shop via OAuth) |
| `PHONE_NUMBER_ID` | ☐ | Legacy fallback phone number ID |
| `WEBHOOK_VERIFY_TOKEN` | ✅ | Any random string — must match Meta dashboard setting |
| `REDIS_URL` | ✅ | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | ✅ | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | ✅ | `redis://localhost:6379/1` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins |
| `RATE_LIMIT_LOGIN` | ☐ | `10/15minutes` (default) |
| `SENTRY_DSN` | ☐ | Sentry DSN for error monitoring — leave blank to disable |

---

## API Reference

All endpoints are prefixed with `/api/v1` unless noted. Protected endpoints require `Authorization: Bearer <token>`.

### Authentication

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/auth/register` | — | Register a new shop account |
| `POST` | `/api/v1/auth/login` | — | Log in — returns JWT access token |
| `POST` | `/api/v1/auth/refresh` | ✅ | Refresh access token |

### Orders

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/api/v1/orders` | ✅ | List orders — filters: `status`, `customer_id`, `from_date`, `to_date`, `page`, `size` |
| `GET` | `/api/v1/orders/{id}` | ✅ | Order detail with customer and full message thread |
| `PATCH` | `/api/v1/orders/{id}/status` | ✅ | Update status + auto-notify customer via WhatsApp |
| `PATCH` | `/api/v1/orders/{id}/notes` | ✅ | Update notes and/or total amount |
| `POST` | `/api/v1/orders/{id}/reply` | ✅ | Send a manual WhatsApp reply to customer |

### Customers

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/api/v1/customers` | ✅ | List customers (paginated) |
| `GET` | `/api/v1/customers/{id}` | ✅ | Customer profile |
| `GET` | `/api/v1/customers/{id}/orders` | ✅ | All orders for a customer |
| `PATCH` | `/api/v1/customers/{id}` | ✅ | Update customer display name |

### Shop Profile

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/api/v1/shop/profile` | ✅ | Get shop profile and settings |
| `PATCH` | `/api/v1/shop/profile` | ✅ | Update name and phone number |
| `PATCH` | `/api/v1/shop/hours` | ✅ | Update business hours |

### WhatsApp Connections (OAuth)

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/api/v1/connections` | ✅ | List connected WhatsApp accounts |
| `POST` | `/api/v1/connections/oauth/init` | ✅ | Start OAuth flow — returns redirect URL |
| `GET` | `/api/v1/connections/oauth/callback` | — | Meta OAuth callback (redirect target) |
| `DELETE` | `/api/v1/connections/{id}` | ✅ | Disconnect a WhatsApp account |

### Webhook (called by Meta — no auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/webhook` | Meta webhook verification handshake |
| `POST` | `/webhook` | Inbound message handler |

### Conversations

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/api/v1/conversations` | ✅ | List conversation threads (paginated) |
| `GET` | `/api/v1/conversations/{customer_id}` | ✅ | Full message thread with a customer |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |

> Full interactive docs available at `/docs` (Swagger UI) or `/redoc` when the server is running.

---

## WhatsApp Setup

### 1. Create a Meta App

1. Go to [Meta Developers](https://developers.facebook.com) → **My Apps → Create App**.
2. Select **Business** as the app type.
3. Add the **WhatsApp** product.
4. Note your **App ID** and **App Secret** → set as `META_APP_ID` and `META_APP_SECRET`.

### 2. Configure Webhook

1. In the Meta dashboard, go to **WhatsApp → Configuration → Webhook**.
2. Set **Callback URL** to `<BACKEND_URL>/webhook`.
3. Set **Verify Token** to the same value as `WEBHOOK_VERIFY_TOKEN` in `.env`.
4. Subscribe to **messages** events.

### 3. Register Message Templates

Status change notifications use pre-approved WhatsApp templates. Register these in **Meta Business Manager → WhatsApp → Message Templates**:

| Template Name | Language | Message Text |
|--------------|----------|--------------|
| `order_received` | en_US | Thank you! Your order has been received. We will confirm shortly. |
| `order_confirmed` | en_US | Your order is confirmed! We are preparing it now. |
| `order_ready` | en_US | Your order is ready for pickup / out for delivery! |
| `order_delivered` | en_US | Your order has been delivered. Thank you for ordering from us! |
| `order_cancelled` | en_US | Sorry, your order has been cancelled. Please contact us for more info. |

Templates require Meta approval (typically a few minutes to a few hours).

### 4. Connect a Shop (OAuth Flow)

1. Register a shop via `POST /api/v1/auth/register`.
2. Log in and open the dashboard **Settings → WhatsApp Connection**.
3. Click **Connect WhatsApp** — initiates Meta OAuth.
4. Approve the connection in Meta — the access token is stored encrypted in the database.

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe the change"

# Show migration history
alembic history
```

### Schema Overview

```
shops               — tenant (shop owner account)
  └── customers     — scoped to shop
  └── orders        — scoped to shop, linked to customer
      └── messages  — inbound/outbound WhatsApp messages linked to order
  └── social_connections  — OAuth tokens per WhatsApp Business Account
```

---

## Running Tests

Tests use an in-memory SQLite database — no live PostgreSQL or Redis required.

```bash
# Run all tests
pytest app/tests/ -v

# Run with coverage
pytest app/tests/ --cov=app --cov-report=term-missing

# Run a specific test file
pytest app/tests/test_orders.py -v
```

---

## Project Structure

```
whatsapp-order-api/
├── app/
│   ├── core/
│   │   ├── config.py          # pydantic-settings configuration
│   │   ├── database.py        # Async SQLAlchemy engine + session factory
│   │   ├── encryption.py      # Fernet encrypt/decrypt helpers
│   │   ├── security.py        # JWT creation/validation, bcrypt
│   │   └── logging.py         # structlog setup
│   ├── models/                # SQLAlchemy ORM models
│   │   ├── shop.py
│   │   ├── customer.py
│   │   ├── order.py
│   │   ├── message.py
│   │   └── social_connection.py
│   ├── schemas/               # Pydantic request/response schemas
│   ├── repositories/          # Data access layer (Repository pattern)
│   ├── services/              # Business logic
│   │   ├── whatsapp_service.py   # Meta Cloud API integration
│   │   ├── order_service.py      # Order lifecycle management
│   │   └── meta_oauth_service.py # OAuth token exchange + refresh
│   ├── api/v1/
│   │   ├── endpoints/         # FastAPI routers (auth, orders, customers, …)
│   │   └── api.py             # Router aggregation
│   ├── tasks/
│   │   ├── celery_app.py      # Celery app factory
│   │   ├── order_tasks.py     # send_daily_summaries, cleanup_old_messages
│   │   └── token_tasks.py     # Token refresh task
│   ├── middleware/            # CORS, RequestID, RateLimit, ErrorHandler
│   ├── utils/
│   │   ├── order_parser.py    # Free-text → structured order
│   │   └── validators.py      # Phone number, etc.
│   ├── tests/                 # pytest test suite
│   └── main.py                # FastAPI app factory + lifespan
├── alembic/                   # Database migrations
│   └── versions/
│       ├── 0001_initial_schema.py
│       └── 0002_add_social_connections.py
├── scripts/
│   └── generate_encryption_key.py
├── .env.example               # Template — copy to .env and fill in secrets
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml             # Build config + ruff + mypy
└── requirements.txt
```

---

## Deployment

### Docker Compose (recommended for self-hosting)

```bash
# Production — set ENVIRONMENT=production in .env
docker-compose up -d --build
docker-compose exec api alembic upgrade head
```

### Render / Railway / Fly.io

1. Set all environment variables in the platform's dashboard.
2. Build command: `pip install -r requirements.txt && alembic upgrade head`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Deploy Celery worker as a separate service with start command:
   `celery -A app.tasks.celery_app worker --loglevel=info`

### Production Checklist

- [ ] `ENVIRONMENT=production` in env
- [ ] Strong, unique `ENCRYPTION_KEY` and `JWT_SECRET_KEY`
- [ ] `BACKEND_URL` set to your public HTTPS domain
- [ ] `CORS_ORIGINS` restricted to your frontend domain only
- [ ] Meta webhook pointing to your public HTTPS domain
- [ ] WhatsApp templates approved in Meta Business Manager
- [ ] Redis and PostgreSQL accessible (managed services recommended)
- [ ] `SENTRY_DSN` configured for error monitoring

---

## Contributing

1. Fork the repo and create a feature branch.
2. Install dev dependencies: `pip install -r requirements.txt`
3. Follow existing code style (ruff + mypy strict mode enforced in `pyproject.toml`).
4. Write tests for new functionality.
5. Open a PR with a clear description of the change and why.

---

## License

MIT
