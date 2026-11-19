
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

### Planned
- PostgreSQL
- SQLAlchemy
- Alembic
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
├── app/
│   ├── __init__.py
│   └── main.py
├── tests/
│   └── test_main.py
├── .gitignore
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

### 5. Run the application

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
- [ ] PostgreSQL database integration
- [ ] Database models and migrations
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
