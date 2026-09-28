# EVE Healthcare — SDE Intern Backend Assignment

A robust backend service for diagnostic test bookings and simulated payments, designed to fulfill the requirements of the SDE Intern Backend Engineering Assignment.

**Stack:** FastAPI · SQLAlchemy 2 · PostgreSQL / SQLite · Redis · JWT · Docker Compose

---

## Assignment Requirements Checklist

- [x] **Authentication**: JWT-based User signup & login.
- [x] **Diagnostic Centres & Tests**: API to manage and retrieve centres, locations, tests, and prices.
- [x] **Booking System**: Authenticated users can book tests (Patient, Test, Centre, Appointment, Amount, Status: `PENDING`, `CONFIRMED`, `FAILED`, `CANCELLED`).
- [x] **Simulated Payment Service**: Mock `/payments/` endpoint resulting in `SUCCESS` or `FAILED`.
- [x] **Payment Webhook**: Idempotent webhook endpoint (`/payments/webhook/`) that prevents duplicate payments or corrupted states.
- [x] **Edge Cases**: Handled invalid requests, unauthorized modifications, and webhook idempotency gracefully.

---

## How to run the project locally

You can run this project using Docker (recommended) or locally using Python.

### Option 1: Quick start (Docker)

```bash
docker compose up --build
```
This will spin up the API, PostgreSQL database, and Redis.
- API: http://localhost:8000  
- Swagger UI: http://localhost:8000/docs  

### Option 2: Local development (Using SQLite/PostgreSQL)

If you don't have Docker or PostgreSQL installed, you can run the project locally using SQLite.

```bash
# 1. Create a virtual environment and activate it
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file (Defaults to SQLite if Postgres is unavailable)
cp .env.example .env

# 4. Run database migrations (or create tables) and seed initial data
python -c "from app.db import engine, Base; from app.models.user import User; from app.models.centre import DiagnosticCentre, CentreTest; from app.models.booking import Booking; from app.models.payment import Payment, PaymentWebhookEvent; Base.metadata.create_all(bind=engine)"
python -m app.seed

# 5. Start the server
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs to view the Swagger UI. (Note: If Redis is not running, the API still works; centre endpoints simply skip caching).

---

## API endpoints and example requests

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

**1. Signup**
```bash
curl -s -X POST http://localhost:8000/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"patient@example.com","password":"password123","full_name":"Ada Patient"}'
```

**2. Login**
```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"patient@example.com","password":"password123"}'
```

**3. Create Booking** (replace `TOKEN`)
```bash
curl -s -X POST http://localhost:8000/bookings/ \
  -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"centre_id":"CENTRE_UUID", "centre_test_id":"TEST_UUID", "appointment_at":"2026-12-01T10:00:00Z"}'
```

**4. Payment webhook** (idempotent on `event_id`)
```bash
curl -s -X POST http://localhost:8000/payments/webhook/ \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: dev-webhook-secret' \
  -d '{"event_id":"evt_001", "provider_payment_id":"pay_001", "status":"SUCCESS"}'
```

---

## Database schema design

| Table | Purpose |
|-------|---------|
| `users` | Stores authenticated user accounts |
| `diagnostic_centres` | Stores diagnostic centres (name, location) |
| `centre_tests` | Tests offered by a centre along with their prices |
| `bookings` | User booking details: centre, test, appointment time, amount, and status |
| `payments` | Tracks payments (one payment record per booking, `booking_id` is unique) |
| `payment_webhook_events` | Stores processed webhook `event_id`s with a unique constraint to ensure idempotency |

**State Transitions:**
- **Booking statuses:** `PENDING` → `CONFIRMED` | `FAILED` | `CANCELLED`  
- **Payment statuses:** `SUCCESS` | `FAILED`

---

## Important assumptions made

- **Seeded Data:** Centres and tests are seeded automatically on startup. Admin CRUD operations were omitted to keep the scope strictly focused on the core booking and payment flow.
- **Price Immutability:** The booking amount is copied from the test price at the exact time of booking. Future price changes will not retroactively alter past bookings.
- **One Payment Per Booking:** Paying a non-`PENDING` booking returns a `409 Conflict`.
- **Payment Simulation:** The simulated payment succeeds with a probability of `PAYMENT_SUCCESS_RATE` (default `0.8`) unless `force_status` is explicitly set in the request.
- **Webhook Authentication:** Webhook auth relies on a shared secret header (`X-Webhook-Secret`), not a user JWT, reflecting real-world provider integrations.
- **Graceful Degradation:** Redis cache failures are handled non-fatally; the API simply falls back to serving data directly from the DB.
- **Cancellations:** Users are only allowed to cancel their own `PENDING` bookings.

---

## What I would improve if I had more time

- **Admin Dashboard & CRUD:** Implement an admin role with full CRUD capabilities for managing diagnostic centres and tests.
- **Background Processing:** Integrate Celery or a background job queue to handle webhook retries and outbound provider calls asynchronously.
- **Rate Limiting:** Add rate-limiting middlewares (e.g., via Redis) on authentication and webhook endpoints to prevent abuse.
- **Advanced Webhook Security:** Implement stronger webhook payload signatures (e.g., HMAC with timestamp skew validation) instead of a static shared secret.
- **Capacity Management:** Add logic for appointment slot conflict checks and daily capacity limits for centres.
- **CI/CD Pipeline:** Set up GitHub Actions to automatically run `pytest`, `flake8`, and `black` on every push to ensure code quality.

---

## Tests

Unit and integration tests are included (covering auth, bookings, payments, and webhook idempotency).
Tests use an in-memory SQLite database so no external dependencies are required.

```bash
pytest -v
```
