# TaskFlow API

A RESTful backend API for user, project, and task management, built with Python, FastAPI, and PostgreSQL.

## Overview

TaskFlow API is an incremental software engineering project focused on modular architecture, secure authentication and authorization, relational database design, and automated testing.

The long-term goal is to manage users, projects, and tasks through a maintainable REST API. **User registration, login, profile management, and initial administrator operations are implemented.** Project and task management features are planned, not yet available.

**Project status:** In Development  
**Current API version:** `0.1.0`

## Tech Stack

### Backend

- Python 3.12
- FastAPI and Uvicorn
- Pydantic and Pydantic Settings
- Pydantic `EmailStr` for email validation
- `python-multipart` for OAuth2 password-form submissions

### Database

- PostgreSQL
- SQLAlchemy 2.0 ORM
- Psycopg 3
- Alembic migrations

### Authentication and Security

- `pwdlib` with Argon2 password hashing
- PyJWT with HS256-signed access tokens
- OAuth2 password-form login and Bearer authentication
- Database-backed active-account and role checks
- Basic role-based access control (RBAC): `user` and `admin`
- Environment-based secret configuration

### Testing and Quality

- pytest and pytest-cov
- FastAPI `TestClient` / HTTPX
- Isolated in-memory SQLite databases for API tests
- `unittest.mock` for targeted database error and session-lifecycle tests
- Statement and branch coverage reporting

### Planned Tools

- Ruff
- Docker
- GitHub Actions

## Implemented Features

### API Architecture

- Modular routing, services, Pydantic schemas, SQLAlchemy models, and database modules
- Versioned API endpoints under `/api/v1`
- Root and health-check endpoints
- Automatic OpenAPI specification and interactive Swagger UI
- Dependency injection for database access and authentication

### Database Integration

- PostgreSQL connection and SQLAlchemy session management
- `User` model and Alembic-managed schema migrations
- Initial users-table migration (`b50570e674cd`)
- User profile and role migration (`e9e1baaf2074`)
- Environment-based database configuration

### Registration and Authentication

- Registration using validated email and password (8–128 characters)
- Email normalization and duplicate-email handling (`409 Conflict`)
- Argon2 password hashing; no plaintext password storage
- Login with email supplied in the OAuth2 `username` form field
- Rejection of incorrect credentials and inactive accounts
- JWT creation and validation (signature, expiration, required claims, access-token type, and user ID)
- Configurable access-token expiration (default: 30 minutes)
- Protected current-user endpoint backed by a database lookup
- API response schemas that exclude passwords and stored password hashes

### User Profile Management

- `GET /api/v1/users/me` to retrieve the authenticated user's profile
- `PATCH /api/v1/users/me` to update the optional `full_name` field
- Name trimming and validation; optional clearing with `null`
- Rejection of unapproved profile fields such as `role` and `is_active`
- The user's identity comes from the verified JWT, not a user-supplied ID

### Role-Based Authorization and Administration

- Basic `user` / `admin` roles; new registrations default to `user`
- Reusable `get_current_user` and `require_admin` dependencies
- `401 Unauthorized` for missing, invalid, or expired authentication
- `403 Forbidden` for authenticated users without admin privileges
- Admin-only aggregate user statistics
- Admin-only user listing with pagination (`offset`, `limit`)
- Admin-only activation/deactivation of non-admin accounts
- Protection against status changes to admin accounts through the management endpoint
- Immediate rejection of protected requests from deactivated accounts, including requests carrying previously issued tokens

**Admin provisioning:** Public registration does **not** grant admin privileges, and this project does not yet provide an admin-provisioning API or CLI. Admin functionality is currently verified with temporary admin records created inside isolated tests. Do not alter production account roles manually as a substitute for a secure provisioning process.

### Automated Testing

- API smoke tests for root and health-check endpoints
- Password hashing and verification tests
- Registration and duplicate-email tests
- Login tests for valid, invalid, unknown, and inactive accounts
- JWT signature, expiration, claim, token-type, and invalid-ID tests
- Protected profile access and profile update validation tests
- RBAC and administrator operations tests, including pagination and account activation
- Simulated database integrity-error and rollback tests
- Database session cleanup tests for normal and exceptional execution paths

## API Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| `GET` | `/` | Root endpoint | Public |
| `GET` | `/health` | Health check | Public |
| `POST` | `/api/v1/auth/register` | Register a user | Public |
| `POST` | `/api/v1/auth/login` | Log in and obtain JWT | Public |
| `GET` | `/api/v1/users/me` | Get current profile | Authenticated |
| `PATCH` | `/api/v1/users/me` | Update current user's name | Authenticated |
| `GET` | `/api/v1/admin/stats` | User counts | Admin |
| `GET` | `/api/v1/admin/users` | Paginated user list | Admin |
| `PATCH` | `/api/v1/admin/users/{user_id}/status` | Activate/deactivate a non-admin user | Admin |
| `GET` | `/docs` | Swagger UI | Public |
| `GET` | `/openapi.json` | OpenAPI schema | Public |

### 1. Register a User

**Request:** `POST /api/v1/auth/register`  
**Content type:** `application/json`

```json
{
  "email": "testuser@example.com",
  "password": "SecurePass123!"
}
```

**Example response — `201 Created`:**

```json
{
  "id": 1,
  "email": "testuser@example.com",
  "full_name": null,
  "role": "user",
  "is_active": true,
  "created_at": "2026-11-22T12:00:00Z"
}
```

The ID and timestamp are illustrative. Duplicate email addresses return `409 Conflict`; invalid input returns `422`. Neither passwords nor password hashes appear in the response. New users cannot choose their own roles through registration.

### 2. Log In

**Request:** `POST /api/v1/auth/login`  
**Content type:** `application/x-www-form-urlencoded`

Form fields:

- `username`: the user's registered email address
- `password`: the user's password

**Example response — `200 OK`:**

```json
{
  "access_token": "<signed-jwt-access-token>",
  "token_type": "bearer"
}
```

Unknown accounts, incorrect passwords, and inactive accounts return `401 Unauthorized` with a generic credential error. The access token's default lifetime is 30 minutes, controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`.

### 3. View the Current Profile

```http
GET /api/v1/users/me
Authorization: Bearer <signed-jwt-access-token>
```

The response uses the `UserResponse` schema and contains `id`, `email`, `full_name`, `role`, `is_active`, and `created_at`.

### 4. Update the Current Profile

```http
PATCH /api/v1/users/me
Authorization: Bearer <signed-jwt-access-token>
Content-Type: application/json
```

```json
{
  "full_name": "Deniz Yılmaz"
}
```

The endpoint returns the updated user profile (`200 OK`). Sending `{"full_name": null}` removes the name; sending `{}` preserves the current value. Attempts to modify `role`, `is_active`, or other unapproved fields return `422`.

### 5. Administrator Statistics

```http
GET /api/v1/admin/stats
Authorization: Bearer <admin-access-token>
```

Example response (illustrative values):

```json
{
  "total_users": 5,
  "active_users": 4
}
```

### 6. List Users (Admin Only)

```http
GET /api/v1/admin/users?offset=0&limit=20
Authorization: Bearer <admin-access-token>
```

Returns an array of `UserResponse` records. Pagination defaults to `offset=0`, `limit=20`, with a maximum limit of `100`. Password hashes are excluded from the response.

### 7. Change Account Status (Admin Only)

```http
PATCH /api/v1/admin/users/2/status
Authorization: Bearer <admin-access-token>
Content-Type: application/json
```

```json
{
  "is_active": false
}
```

Returns the updated `UserResponse` on success (`200 OK`). Use `true` to reactivate a non-admin user. Missing users return `404`; attempts to change admin accounts through this endpoint return `403`; malformed data returns `422`.

### Authentication and Authorization Rules

| Situation | Status |
|-----------|--------|
| Missing, invalid, or expired token | `401 Unauthorized` |
| Authenticated regular user requesting an admin endpoint | `403 Forbidden` |
| Authenticated, active admin requesting an admin endpoint | `200 OK` (on successful operation) |
| Unknown user ID in admin status update | `404 Not Found` |
| Invalid JSON fields or validation errors | `422 Unprocessable Content` |

**Security:** JWT payloads are signed, **not encrypted**. Do not include passwords or secrets in token claims. Treat access tokens as credentials; never publish real tokens, database passwords, or JWT signing secrets.

## Project Structure

```text
taskflow-api/
├── alembic/
│   ├── versions/
│   │   ├── b50570e674cd_create_users_table.py
│   │   └── e9e1baaf2074_add_user_profile_and_role_fields.py
│   ├── env.py
│   ├── README
│   └── script.py.mako
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       └── routers/
│   │           ├── admin.py
│   │           ├── auth.py
│   │           ├── system.py
│   │           └── users.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   ├── admin.py
│   │   ├── token.py
│   │   └── user.py
│   ├── services/
│   │   ├── admin_service.py
│   │   ├── auth_service.py
│   │   └── user_service.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_admin.py
│   ├── test_auth.py
│   ├── test_edge_cases.py
│   ├── test_jwt.py
│   ├── test_login.py
│   ├── test_main.py
│   ├── test_profile.py
│   └── test_security.py
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

Empty `__init__.py` files, local `.env`, virtual environments, and generated coverage output are omitted for readability. The migration filename shown for `e9e1baaf2074` should match the generated file in your local `alembic/versions` directory.

| Directory | Responsibility |
|-----------|----------------|
| `app/api` | API routers and shared authentication/authorization dependencies |
| `app/core` | Application configuration, password security, JWT utilities |
| `app/db` | SQLAlchemy engine, database sessions, and declarative base |
| `app/models` | ORM database models |
| `app/schemas` | Request validation and response models |
| `app/services` | Registration, login, profile, and administrative business logic |
| `alembic` | Version-controlled PostgreSQL schema migrations |
| `tests` | Automated testing and reusable fixtures |

## Installation

### Prerequisites

- Python 3.12
- A running PostgreSQL server
- Git

The commands below target **Windows PowerShell**.

### 1. Clone the Repository

```powershell
git clone https://github.com/yarendmr/taskflow-api.git
cd taskflow-api
```

### 2. Create and Activate a Virtual Environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create the `taskflow_db` database and a dedicated login role named `taskflow_user`. Configure ownership and permissions so the application can connect and manage its tables.

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Set the appropriate values in your **local** `.env` file:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=taskflow_db
DB_USER=taskflow_user
DB_PASSWORD=replace_with_your_database_password

JWT_SECRET_KEY=replace_with_a_secure_random_secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Generate a strong JWT signing secret locally:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Use the generated value for `JWT_SECRET_KEY`. Never commit `.env` or real secrets. Keep `.env.example` limited to placeholders and non-sensitive defaults.

### 5. Apply Database Migrations

```powershell
alembic upgrade head
alembic current
```

The first migration creates `users`; the second adds optional `full_name` and `role` (default `user`). For the development state described here, the latest revision is `e9e1baaf2074`.

### 6. Run the API

```powershell
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

The `--reload` option is intended for development, not production deployment.

## Running Tests and Coverage

Run the complete test suite:

```powershell
python -m pytest -v
```

Run specific test modules:

```powershell
python -m pytest tests/test_main.py -v
python -m pytest tests/test_security.py -v
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_jwt.py -v
python -m pytest tests/test_login.py -v
python -m pytest tests/test_profile.py -v
python -m pytest tests/test_admin.py -v
python -m pytest tests/test_edge_cases.py -v
```

Measure statement and branch coverage:

```powershell
python -m pytest --cov=app --cov-branch --cov-report=term-missing
```

### Latest Verified Local Test Run

As of **November 22, 2026**, the local test run reported:

| Metric | Result |
|--------|--------|
| Tests | **48 passed**, 0 failed |
| Coverage | **100%** |
| Statements | **279 total, 0 missed** |
| Branches | **32 total, 0 missed / partially covered** |
| Warnings | 1 non-failing dependency deprecation warning |

The remaining warning concerned the Starlette/HTTPX test-client dependency. The short HMAC test-key warning was addressed by replacing the deliberately incorrect signing key with a longer test-only key.

**Coverage is not a correctness guarantee:** 100% measured coverage means that the instrumented statement and branch paths were exercised; it does not establish the absence of defects or production readiness.

### Testing Strategy

- `tests/conftest.py` creates fresh, isolated in-memory SQLite databases for database-dependent API tests.
- FastAPI dependency overrides prevent these tests from modifying development PostgreSQL data.
- Temporary admin users are created **only inside the test database** to verify RBAC.
- `tests/test_profile.py` covers profile updates and forbidden field changes.
- `tests/test_admin.py` covers role checks, pagination, status management, and protected admin accounts.
- `tests/test_edge_cases.py` uses mocks to exercise integrity-error rollback, session cleanup, and JWT edge cases.
- PostgreSQL-specific integration tests are still planned because SQLite behavior is not identical to PostgreSQL behavior.

Generated coverage outputs (`.coverage`, `htmlcov/`, `coverage.xml`) should be excluded from Git with `.gitignore`.

## Database Schema

### `users` Table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer | Primary key |
| `email` | VARCHAR(255) | Unique user email address |
| `full_name` | VARCHAR(120), nullable | Optional profile name |
| `hashed_password` | VARCHAR(255) | Argon2 password hash |
| `role` | VARCHAR(20), default `user` | Authorization role |
| `is_active` | Boolean | Whether the account is active |
| `created_at` | Timestamp with time zone | Account creation timestamp |

The email column has a unique index. All schema changes are applied through Alembic. No plaintext passwords are stored.

## Development Roadmap

### Completed — Days 1–6

- [x] FastAPI setup and modular API architecture
- [x] Root, health-check, and Swagger/OpenAPI endpoints
- [x] PostgreSQL, SQLAlchemy, and Alembic integration
- [x] Users-table and profile/role migrations
- [x] Environment-based settings and secret handling
- [x] Registration, validation, and Argon2 password security
- [x] OAuth2-compatible login and JWT access tokens
- [x] Protected user-profile retrieval and updates
- [x] Basic role-based authorization (`user`, `admin`)
- [x] Admin user statistics and paginated user listing
- [x] Admin-managed account activation and deactivation
- [x] Protection against modifying admin accounts through status endpoint
- [x] Isolated automated API, authorization, and edge-case tests
- [x] Coverage tooling with statement and branch analysis

### Planned

- [ ] Dedicated, secure admin-account provisioning workflow
- [ ] Project and task database models and migrations
- [ ] Project management endpoints
- [ ] Task management and assignment workflows
- [ ] User-project relationships and membership permissions
- [ ] Expanded filtering, sorting, and pagination
- [ ] More granular object-level authorization and permissions
- [ ] Refresh-token and token-revocation strategy, if required
- [ ] Rate limiting, account lockout policy, and additional auth hardening
- [ ] PostgreSQL-specific integration tests and security reviews
- [ ] Ruff linting and formatting
- [ ] Docker containerization
- [ ] GitHub Actions CI pipeline
- [ ] Deployment preparation and production configuration

## Development Approach

TaskFlow API is developed incrementally. API routing, business logic, data validation, security checks, and database access are separated into dedicated modules. Database migrations are version-controlled with Alembic, while automated tests run as features are introduced.

**This is a development-stage project.** Passing tests, high coverage, and basic JWT/RBAC features do not alone make the service production-ready.

## License

No license has been selected yet.
