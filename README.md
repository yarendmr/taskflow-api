# TaskFlow API

A RESTful backend API for user, project, and task management, built with Python, FastAPI, and PostgreSQL.

## Overview

TaskFlow API is an incremental software engineering project focused on modular architecture, secure authentication and authorization, relational database design, and automated testing.

The API currently implements **user registration, JWT authentication, profile management, role-based administrator operations, project management, and project-scoped task management**. Project and task resources are protected by ownership checks, and projects have cascading task deletion.

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
- `User`, `Project`, and `Task` SQLAlchemy models
- Alembic-managed schema migrations for users, user profiles/roles, projects, and tasks
- Foreign key relationships: `projects.owner_id → users.id` and `tasks.project_id → projects.id`
- Database-enforced `ON DELETE CASCADE` from projects to tasks
- Indexed owner/project foreign keys
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

### Project Management (Day 7)

- Create, list, retrieve, partially update, and delete projects
- Every project is owned by its creator (`owner_id` is set server-side)
- Ownership-aware read, update, and deletion operations
- Project statuses: `active`, `completed`, `archived`
- Paginated project listing (`offset`, `limit`)
- Request validation that prevents clients from setting or changing `owner_id`
- `404 Not Found` for nonexistent projects and projects owned by another user

### Task Management (Day 8)

- Create, list, retrieve, partially update, and delete tasks within an owned project
- Task statuses: `todo`, `in_progress`, `done`
- Task priorities: `low`, `medium`, `high` (default `medium`)
- Optional descriptions and timezone-aware due dates
- Paginated task listing within a project (`offset`, `limit`)
- Validation that prevents task reassignment through unapproved `project_id` fields
- Ownership checks on every task operation, with both project and task IDs checked
- Automatic task deletion when the parent project is deleted (`ON DELETE CASCADE`)

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
- Project CRUD, pagination, input validation, and cross-user ownership tests
- Task CRUD, pagination, input validation, and cross-user ownership tests
- Task/project URL mismatch tests
- Cascade-deletion test with SQLite foreign key enforcement enabled

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
| `POST` | `/api/v1/projects` | Create a project | Authenticated |
| `GET` | `/api/v1/projects` | List owned projects | Authenticated |
| `GET` | `/api/v1/projects/{project_id}` | Get an owned project | Owner |
| `PATCH` | `/api/v1/projects/{project_id}` | Update an owned project | Owner |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete an owned project | Owner |
| `POST` | `/api/v1/projects/{project_id}/tasks` | Create a task in an owned project | Project owner |
| `GET` | `/api/v1/projects/{project_id}/tasks` | List tasks in an owned project | Project owner |
| `GET` | `/api/v1/projects/{project_id}/tasks/{task_id}` | Get a project task | Project owner |
| `PATCH` | `/api/v1/projects/{project_id}/tasks/{task_id}` | Update a project task | Project owner |
| `DELETE` | `/api/v1/projects/{project_id}/tasks/{task_id}` | Delete a project task | Project owner |
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

### 8. Create and Manage Projects

Create a project:

```http
POST /api/v1/projects
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "name": "TaskFlow Backend",
  "description": "Implement backend features and tests"
}
```

**Example response — `201 Created`** (IDs and timestamps are illustrative):

```json
{
  "id": 1,
  "name": "TaskFlow Backend",
  "description": "Implement backend features and tests",
  "status": "active",
  "owner_id": 1,
  "created_at": "2026-11-24T12:00:00Z"
}
```

`owner_id` is derived from the authenticated user and cannot be supplied or updated through the API.

Additional project operations:

```http
GET /api/v1/projects?offset=0&limit=20
GET /api/v1/projects/1
PATCH /api/v1/projects/1
DELETE /api/v1/projects/1
```

For project updates, only the provided allowed fields are changed. Example:

```json
{
  "name": "TaskFlow API",
  "status": "completed"
}
```

`name` is required when creating a project (1–150 characters after trimming). `description` is optional (maximum 2,000 characters). Allowed statuses are `active`, `completed`, and `archived`. The update schema rejects explicit `null` for `name` and `status`; `description` may be cleared with `null`.

Project lists include **only the authenticated user's projects**, ordered by ID. Pagination uses `offset >= 0` and `1 <= limit <= 100` (defaults: 0 and 20). Updates return `200 OK`, successful deletions return `204 No Content`, invalid input returns `422`, and missing or unowned projects return `404`.

### 9. Create and Manage Project Tasks

Create a task inside an owned project:

```http
POST /api/v1/projects/1/tasks
Authorization: Bearer <access-token>
Content-Type: application/json
```

```json
{
  "title": "Write JWT tests",
  "description": "Add coverage for security edge cases",
  "priority": "high",
  "due_date": "2026-12-15T18:00:00+03:00"
}
```

**Example response — `201 Created`:**

```json
{
  "id": 1,
  "project_id": 1,
  "title": "Write JWT tests",
  "description": "Add coverage for security edge cases",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-12-15T15:00:00Z",
  "created_at": "2026-11-24T12:00:00Z"
}
```

Timestamp formatting depends on the database and serializer; the values above are illustrative.

Additional task operations:

```http
GET /api/v1/projects/1/tasks?offset=0&limit=20
GET /api/v1/projects/1/tasks/1
PATCH /api/v1/projects/1/tasks/1
DELETE /api/v1/projects/1/tasks/1
```

Example partial update:

```json
{
  "status": "in_progress",
  "priority": "high"
}
```

Tasks start with status `todo` and priority `medium` unless another allowed priority is provided. Allowed statuses are `todo`, `in_progress`, and `done`. Allowed priorities are `low`, `medium`, and `high`. `title` is required on creation (1–150 characters after trimming); `description` is optional (up to 2,000 characters). Due dates, when set, require a timezone offset or `Z`.

Updates accept only allowed task fields. Explicit `null` is rejected for `title`, `status`, and `priority`; `description` and `due_date` can be cleared with `null`. The project is selected from the URL, not a client-controlled JSON `project_id`.

Task lists are scoped to the selected, owned project and ordered by ID. Pagination defaults to `offset=0`, `limit=20`, with `limit` constrained to 1–100. Invalid data returns `422`, absent tokens return `401`, and a task or project the user cannot access returns `404`. Successful task deletion returns `204 No Content`.

**Deletion behavior:** Deleting a project also removes its related task rows through the database foreign key's `ON DELETE CASCADE`. This is verified in the SQLite test suite with foreign key checks explicitly enabled; PostgreSQL integration testing remains a future enhancement.

### Authentication and Authorization Rules

| Situation | Status |
|-----------|--------|
| Missing, invalid, or expired token | `401 Unauthorized` |
| Authenticated regular user requesting an admin endpoint | `403 Forbidden` |
| Authenticated, active admin requesting an admin endpoint | `200 OK` (on successful operation) |
| Unknown user ID in admin status update | `404 Not Found` |
| Invalid JSON fields or validation errors | `422 Unprocessable Content` |
| Project or task absent, or resource not owned by the user | `404 Not Found` |
| Successful project/task creation | `201 Created` |
| Successful project/task deletion | `204 No Content` |

**Security:** JWT payloads are signed, **not encrypted**. Do not include passwords or secrets in token claims. Treat access tokens as credentials; never publish real tokens, database passwords, or JWT signing secrets.

## Project Structure

```text
taskflow-api/
├── alembic/
│   ├── versions/
│   │   ├── b50570e674cd_create_users_table.py
│   │   ├── e9e1baaf2074_add_user_profile_and_role_fields.py
│   │   ├── 3ef95812025f_create_projects_table.py
│   │   └── 94f69fd864b7_create_tasks_table.py
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
│   │           ├── projects.py
│   │           ├── system.py
│   │           ├── tasks.py
│   │           └── users.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── project.py
│   │   ├── task.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── admin.py
│   │   ├── project.py
│   │   ├── task.py
│   │   ├── token.py
│   │   └── user.py
│   ├── services/
│   │   ├── admin_service.py
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── task_service.py
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
│   ├── test_projects.py
│   ├── test_security.py
│   └── test_tasks.py
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

Empty `__init__.py` files, local `.env`, the virtual environment, and generated coverage output are omitted for readability. Migration file names correspond to the revisions described in the project.

| Directory | Responsibility |
|-----------|----------------|
| `app/api` | API routers and shared authentication/authorization dependencies |
| `app/core` | Configuration, password security, and JWT utilities |
| `app/db` | SQLAlchemy engine, sessions, and declarative base |
| `app/models` | User, project, and task ORM models |
| `app/schemas` | Request validation and response models |
| `app/services` | Business logic, owner-scoped database operations, and administrative services |
| `alembic` | Version-controlled PostgreSQL schema migrations |
| `tests` | Automated tests, SQLite fixtures, and database behavior checks |

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

The Alembic migration chain is:

| Revision | Change |
|----------|--------|
| `b50570e674cd` | Create `users` |
| `e9e1baaf2074` | Add user `full_name` and `role` |
| `3ef95812025f` | Create `projects` |
| `94f69fd864b7` | Create `tasks` with cascading project foreign key |

**Expected migration head as of November 24, 2026:** `94f69fd864b7`.

To verify schema consistency after applying migrations:

```powershell
alembic check
```

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
python -m pytest tests/test_projects.py -v
python -m pytest tests/test_tasks.py -v
```

Measure statement and branch coverage:

```powershell
python -m pytest --cov=app --cov-branch --cov-report=term-missing
```

### Latest Verified Local Test Run

As of **November 24, 2026**, the local test run reported:

| Metric | Result |
|--------|--------|
| Tests | **123 passed**, 0 failed |
| Combined statement and branch coverage | **100%** |
| Statements | **551 total, 0 missed** |
| Branches | **84 total, 0 missed / partially covered** |
| Warnings | **1 non-failing warning** |

The source-specific warning message is not included in this summary; run pytest with warnings visible to inspect its current cause.

**Coverage is not a correctness guarantee:** 100% measured coverage means that the instrumented statement and branch paths were exercised; it does not establish the absence of defects or production readiness.

### Testing Strategy

- `tests/conftest.py` creates fresh, isolated in-memory SQLite databases for database-dependent API tests.
- FastAPI dependency overrides prevent these tests from modifying development PostgreSQL data.
- Temporary admin users are created **only inside the test database** to verify RBAC.
- `tests/test_profile.py` covers profile updates and forbidden field changes.
- `tests/test_admin.py` covers role checks, pagination, status management, and protected admin accounts.
- `tests/test_edge_cases.py` uses mocks to exercise integrity-error rollback, session cleanup, and JWT edge cases.
- `tests/test_projects.py` covers owner-scoped project CRUD, validation, pagination, and cascade deletion.
- `tests/test_tasks.py` covers task CRUD, pagination, validation, and cross-user/cross-project access.
- The SQLite engine enables `PRAGMA foreign_keys=ON` so tests can exercise database-enforced cascade deletion.
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

The email column has a unique index. No plaintext passwords are stored.

### `projects` Table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer | Primary key |
| `name` | VARCHAR(150) | Required project name |
| `description` | Text, nullable | Optional description |
| `status` | VARCHAR(20), default `active` | Project lifecycle status |
| `owner_id` | Integer, indexed | Foreign key to `users.id` |
| `created_at` | Timestamp with time zone | Project creation timestamp |

`owner_id` is determined from the JWT-authenticated user, not from user-controlled JSON. The project status is restricted at the API layer to `active`, `completed`, or `archived`.

### `tasks` Table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer | Primary key |
| `project_id` | Integer, indexed | Foreign key to `projects.id` |
| `title` | VARCHAR(150) | Required task title |
| `description` | Text, nullable | Optional description |
| `status` | VARCHAR(20), default `todo` | Task progress status |
| `priority` | VARCHAR(10), default `medium` | Task priority |
| `due_date` | Timestamp with time zone, nullable | Optional due date |
| `created_at` | Timestamp with time zone | Task creation timestamp |

The `tasks.project_id` foreign key uses `ON DELETE CASCADE`, so a database-level project deletion also deletes its related tasks. Task status and priority values are validated by Pydantic.

**Relationship:** `users (1) → (many) projects (1) → (many) tasks`.

Schema changes are applied through Alembic. The database currently stores status and priority as strings, while the API restricts allowed values through request schemas.

## Development Roadmap

### Completed — Days 1–6

- [x] FastAPI setup, modular API architecture, and health endpoint
- [x] PostgreSQL, SQLAlchemy 2.0, session management, and Alembic
- [x] Environment-based application configuration
- [x] Registration, email validation, and Argon2 password hashing
- [x] OAuth2 password-form login and signed JWT access tokens
- [x] Protected profile retrieval and limited profile updates
- [x] Basic `user`/`admin` authorization and admin user management
- [x] Automated authentication, authorization, and edge-case testing
- [x] Statement and branch coverage reporting

### Completed — Day 7: Project Management

- [x] `Project` model and `3ef95812025f` migration
- [x] `ProjectCreate`, `ProjectUpdate`, and `ProjectResponse` schemas
- [x] Create, list, retrieve, update, and delete owned projects
- [x] Ownership checks, pagination, and input validation
- [x] Project endpoint and cross-user access tests

### Completed — Day 8: Task Management

- [x] `Task` model and `94f69fd864b7` migration
- [x] Task creation, retrieval, listing, updates, and deletion
- [x] Task status and priority validation; optional due dates
- [x] User- and project-scoped task ownership checks
- [x] Database-enforced cascade deletion of tasks with projects
- [x] Cascade test with SQLite foreign keys enabled
- [x] **123 passing tests, 100% statement and branch coverage** on the latest local run

### Planned

- [ ] Dedicated, secure admin-account provisioning workflow
- [ ] Task assignment and project collaboration/membership features
- [ ] Expanded filtering and sorting capabilities
- [ ] More granular object-level authorization where collaboration is introduced
- [ ] Refresh-token/revocation strategy if needed
- [ ] Rate limiting, account lockout policy, and additional authentication hardening
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
