# EVE Healthcare — Diagnostic Booking API

Backend service for diagnostic test bookings and simulated payments.

**Stack:** FastAPI · SQLAlchemy 2 · PostgreSQL · Redis · JWT · Docker Compose

---

## Quick start (Docker)

```bash
docker compose up --build
```

API: http://localhost:8000  
Swagger UI: http://localhost:8000/docs  
Health: http://localhost:8000/health

On startup the API runs migrations and seeds sample centres/tests.

---

## Local development (no Docker)

You still need **PostgreSQL** and **Redis** running on your machine. Docker files stay in the repo for optional use; they are not required.

### 1. Install & start dependencies (Homebrew on macOS)

```bash
# If not already installed:
brew install postgresql@17 redis

brew services start postgresql@17
brew services start redis
```

Create the DB user/database once:

```bash
createuser -s eve 2>/dev/null || true
psql postgres -c "ALTER USER eve WITH PASSWORD 'eve';" 2>/dev/null || \
  psql postgres -c "CREATE USER eve WITH PASSWORD 'eve' SUPERUSER;"
createdb -O eve eve_healthcare 2>/dev/null || true
```

If `psql` / `createuser` are not on your PATH:

```bash
export PATH="$(brew --prefix postgresql@17)/bin:$PATH"
```

### 2. Configure & run the API

```bash
cd /path/to/sanjeetpro
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs

Default `.env` points at:

- `DATABASE_URL=postgresql+psycopg2://eve:eve@localhost:5432/eve_healthcare`
- `REDIS_URL=redis://localhost:6379/0`

If Redis is down, the API still works — centre endpoints just skip caching.

### 3. Tests (no Postgres/Redis needed)

```bash
source .venv/bin/activate
pytest -q
```

---

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

Tests use an in-memory SQLite database (no Docker required).

---

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | — | Register user |
| POST | `/auth/login` | — | Get JWT |
| GET | `/centres/` | JWT | List centres (paginated, Redis-cached) |
| GET | `/centres/{id}` | JWT | Centre + active tests |
| GET | `/centres/{id}/tests` | JWT | List tests (paginated) |
| POST | `/bookings/` | JWT | Create booking (`PENDING`) |
| GET | `/bookings/` | JWT | List own bookings |
| GET | `/bookings/{id}` | JWT | Get own booking |
| POST | `/bookings/{id}/cancel` | JWT | Cancel `PENDING` booking |
| POST | `/payments/` | JWT | Simulate payment |
| POST | `/payments/webhook/` | `X-Webhook-Secret` | Idempotent payment status update |

### Example requests

**Signup**

```bash
curl -s -X POST http://localhost:8000/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"patient@example.com","password":"password123","full_name":"Ada Patient"}'
```

**Login**

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"patient@example.com","password":"password123"}'
```

**List centres** (replace `TOKEN`)

```bash
curl -s http://localhost:8000/centres/ \
  -H "Authorization: Bearer TOKEN"
```

**Create booking**

```bash
curl -s -X POST http://localhost:8000/bookings/ \
  -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "centre_id":"CENTRE_UUID",
    "centre_test_id":"TEST_UUID",
    "appointment_at":"2026-12-01T10:00:00Z"
  }'
```

**Simulate payment** (`force_status` is optional; useful for demos/tests)

```bash
curl -s -X POST http://localhost:8000/payments/ \
  -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"booking_id":"BOOKING_UUID","force_status":"SUCCESS"}'
```

**Payment webhook** (idempotent on `event_id`)

```bash
curl -s -X POST http://localhost:8000/payments/webhook/ \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: docker-dev-webhook-secret' \
  -d '{
    "event_id":"evt_001",
    "provider_payment_id":"pay_...",
    "status":"SUCCESS"
  }'
```

Repeating the same `event_id` returns `already_processed` and does not change state again.

---

## Database schema

| Table | Purpose |
|-------|---------|
| `users` | Auth accounts |
| `diagnostic_centres` | Centres (name, location) |
| `centre_tests` | Tests offered by a centre + price |
| `bookings` | User booking: centre, test, appointment, amount, status |
| `payments` | One payment per booking (`booking_id` unique) |
| `payment_webhook_events` | Processed webhook `event_id`s (unique → idempotency) |

**Booking statuses:** `PENDING` → `CONFIRMED` | `FAILED` | `CANCELLED`  
**Payment statuses:** `SUCCESS` | `FAILED`

---

## Design notes & assumptions

- Centres/tests are **seeded**; no admin CRUD (keeps scope focused on booking + payments).
- Amount is copied from the test price at booking time (price changes later do not rewrite past bookings).
- One payment record per booking; paying a non-`PENDING` booking returns `409`.
- Simulated payment succeeds with probability `PAYMENT_SUCCESS_RATE` (default `0.8`) unless `force_status` is set.
- Webhook auth is a shared secret header (`X-Webhook-Secret`), not JWT.
- Webhook idempotency: unique constraint on `event_id`; duplicates return `200` with `already_processed`.
- Redis cache failures are non-fatal (API still serves from DB).
- Cancel is allowed only for `PENDING` bookings owned by the caller.

---

## Bonus features included

- Docker + docker-compose (API, Postgres, Redis)
- OpenAPI/Swagger at `/docs`
- Redis caching for centre listing/detail/tests
- Structured JSON logging with request IDs
- Pagination (`skip` / `limit`) on list endpoints
- Unit/integration tests (auth, bookings, payments, webhook idempotency)

---

## If I had more time

- Admin role + CRUD for centres/tests
- Celery retries for webhook/outbound provider calls
- Rate limiting on auth and webhook endpoints
- Stronger webhook signatures (HMAC + timestamp skew)
- Appointment slot conflict checks / capacity limits
- CI pipeline (GitHub Actions) running pytest against Postgres
