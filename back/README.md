# VeloSim Backend API

## 🏗️ Architecture

```
back/
├── __init__.py
├── main.py              # FastAPI application entry point
├── core/
│   ├── __init__.py
│   └── config.py        # Application configuration and settings
├── database/
│   ├── __init__.py
│   ├── init.sql         # Database initialization scripts
│   └── session.py       # Database session management
├── models/              # SQLAlchemy database models
├── schemas/             # Pydantic request/response schemas
├── crud/                # Database CRUD operations
├── api/                 # FastAPI route definitions
├── alembic/             # Database migration files
└── tests/
    ├── __init__.py
    └── test_*.py        # Backend API tests
```

## 🚀 Development Commands

> **Note**: All setup instructions (Python installation, virtual environment creation, etc.) are in the [root README](../README.md). This document focuses on backend-specific development workflows.

### Running the Backend Server

```bash
# Start development server (from project root)
npm run dev:backend

# Or manually
python -m uvicorn back.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Operations

VeloSim uses PostgreSQL with Alembic for database migrations. These commands can be run at root level.

**Prerequisites:**

- PostgreSQL running on port 5433 (via Docker: `npm run dev:db`)
- Python environment with Alembic installed

#### Quick Start

```bash
# From project root - Start PostgreSQL database
npm run dev:db

# Check current migration status
npm run db:current

# Apply pending migrations
npm run db:upgrade

# Seed database with initial data
npm run db:seed

# OR: Complete database reset (drop, migrate, seed)
npm run db:dropseed
```

#### Migration Commands

```bash
# Check current migration status
npm run db:current
npm run db:status          # alias for current

# Generate new migration
npm run db:generate "Add new table"

# Apply pending migrations
npm run db:upgrade

# Seed database with initial data
npm run db:seed

# Complete database reset (drop, migrate, seed)
npm run db:dropseed

# Rollback last migration
npm run db:downgrade

# Show migration history
npm run db:history

# Direct Alembic commands (from back/ directory)
cd back
alembic current            # Check current status
alembic upgrade head       # Apply migrations
alembic revision --autogenerate -m "message"  # Generate migration
```

## ⚙️ Configuration

### Environment Variables

Configure these variables in your `.env` file (see [root README](../README.md) for setup):

| Variable             | Description                                               | Default Value                                                | Required |
| -------------------- | --------------------------------------------------------- | ------------------------------------------------------------ | -------- |
| `ENVIRONMENT`        | Application environment                                   | `development`                                                | No       |
| `DEBUG`              | Enable debug mode                                         | `true`                                                       | No       |
| `DATABASE_URL`        | PostgreSQL connection string                              | `postgresql://velosim:velosim@localhost:5433/velosim`        | Yes      |
| `VELOSIM_JWT_SECRET` | JWT signing key, must be consistent for entire deployment | Auto-generated every startup (will kill sessions on restart) | No       |

**Environment Options:**

- `development`: Full debugging, API docs enabled
- `production`: Optimized performance, API docs disabled
- `testing`: Used for test runs

### Hardcoded Settings

The following settings are configured in `back/core/config.py`:

| Setting           | Value                   | Description                          |
| ----------------- | ----------------------- | ------------------------------------ |
| `API_V1_PREFIX`   | `/api/v1`               | API version prefix for all endpoints |
| `ALLOWED_ORIGINS` | Multiple localhost URLs | CORS allowed origins for development |

## 🛠️ Development

### Testing

```bash
# Run backend tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run with coverage (focused on core business logic)
python -m pytest --cov --cov-report=term-missing

# Run with coverage HTML report
python -m pytest --cov --cov-report=html

# Run specific test file
python -m pytest tests/test_*.py
```

## 🏗️ Development Guide

For detailed instructions on implementing new features, see the [Backend Development Workflow](./DEVELOPMENT.md).

This guide covers:

- Step-by-step feature implementation
- Code architecture patterns
- Database migrations
- Testing best practices
- Common pitfalls to avoid

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 🔧 Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.12+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Validation**: Pydantic
- **Testing**: pytest
- **Code Quality**: Black, Flake8, MyPy

## 📄 Related Documentation

- [Backend Development Workflow](./DEVELOPMENT.md) - Complete guide for implementing new features
- [Main Project README](../README.md) - Project setup and overview
- [Frontend README](../front/README.md) - Frontend development guide
- [Simulation Documentation](../sim/) - Simulation engine details
