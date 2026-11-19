
# TaskFlow API

A RESTful task and project management API built with Python and FastAPI.

## Overview

TaskFlow API is a backend development project designed to provide a structured and scalable solution for managing users, projects, and tasks.

The project focuses on REST API design, authentication, database integration, automated testing, and maintainable software architecture.

**Project Status:** In Development

## Tech Stack

### Currently Used
- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- pytest
- HTTPX
- PostgreSQL
- SQLAlchemy 2.0
- Psycopg 3
- Alembic
- Pydantic Settings

### Planned
- JWT Authentication
- Ruff
- Docker
- GitHub Actions

## Implemented Features

- REST API initialization
- Root endpoint
- Health check endpoint
- Interactive Swagger documentation
- Automated endpoint tests
- Modular API architecture with APIRouter
- Environment-based configuration
- PostgreSQL database integration
- SQLAlchemy User model
- Alembic database migrations

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Root endpoint |
| GET | /health | Application health check |
| GET | /docs | Swagger UI documentation |
| GET | /openapi.json | OpenAPI specification |

## Project Structure

```text
taskflow-api/
├── alembic/
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── routers/
│   │           └── system.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
│   └── test_main.py
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yarendmr/taskflow-api.git
cd taskflow-api
```

### 2. Create a virtual environment

```powershell
py -3.12 -m venv .venv
```

### 3. Activate the virtual environment (Windows PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Database Configuration

TaskFlow API uses PostgreSQL to store application data.

Before running the application:

1. Ensure that PostgreSQL is installed and running.
2. Create a database named `taskflow_db`.
3. Create a dedicated database user named `taskflow_user`.
4. Assign ownership of the database to `taskflow_user`.

Copy the environment configuration template:

```powershell
Copy-Item .env.example .env
```

Update the `.env` file with your PostgreSQL credentials.

Apply the database migrations:

```powershell
alembic upgrade head
```

This command creates the required database tables.

**Note:** Never commit the `.env` file or database passwords to version control.

### 6. Run the application

```powershell
python -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000

Swagger UI: http://127.0.0.1:8000/docs

## Running Tests

Run the automated tests using:

```powershell
python -m pytest -v
```

Current automated tests cover the root and health check endpoints.

## Development Roadmap

- [x] Initial FastAPI setup
- [x] Basic API endpoints
- [x] Automated endpoint tests
- [x] PostgreSQL database integration
- [x] Initial User model and database migration
- [ ] Additional database models and migrations
- [ ] User registration and authentication
- [ ] JWT-based authorization
- [ ] Role-based access control
- [ ] Project management endpoints
- [ ] Task management endpoints
- [ ] Filtering and pagination
- [ ] Expanded automated testing
- [ ] Docker containerization
- [ ] CI pipeline with GitHub Actions

## License

No license has been selected yet.
