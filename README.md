<div align="center">

<img style="height: 6em;" src="TeamLogo.png" alt="TeamLogo"/>

</div>

# VeloSim

**An open-source network simulation platform for managing distributed resources in dynamic environments**

VeloSim is an open-source network simulation platform that enables job dispatchers to manage distributed resources in dynamic environments. Built with a Python backend/simulation engine and a modern JavaScript frontend, VeloSim provides real-time simulation capabilities for bike-sharing systems and similar distributed resource networks. The platform features a FastAPI REST API, SQLAlchemy ORM with PostgreSQL, real-time WebSocket streaming, and a React-based frontend with TypeScript.

## 🚀 Developer Getting Started Guide

### Prerequisites

- **Python 3.11** with pip
- **Node.js 18+** with npm
- **Git**

### Initial Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/vinishamanek/VeloSim.git
   cd VeloSim
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate it
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   # Option A: Use npm script (installs everything)
   npm run setup

   # Option B: Manual setup
   pip install -e .[dev]           # Install Python dependencies
   pre-commit install              # Setup pre-commit hooks
   cd front && npm install && cd.. # Install frontend dependencies
   ```

### Running the System

> **Note:** Activate your virtual environment first if using one:
>
> - Windows: `.venv\Scripts\activate`
> - macOS/Linux: `source .venv/bin/activate`

```bash
# Run all tests
npm run test

# Run tests with coverage
npm run test:coverage

# Lint all code
npm run lint

# Format all code
npm run format
```

### Development Workflow

1. **Create a feature branch** with proper naming:

   ```bash
   git checkout -b feature/123-awesome-feature    # For new features
   git checkout -b bugfix/456-fix-critical-bug    # For bug fixes
   ```

2. **Make changes** following the code standards
3. **Write tests** for new functionality
4. **Run tests locally**: `npm run test`
5. **Commit with proper message**: Must include issue number
   ```
   feat: add user authentication #123
   fix: resolve login bug fixes #456
   ```
6. **Push and create PR** - CI will automatically run

### Project Structure

```
VeloSim/
├── back/           # Python backend API (FastAPI + SQLAlchemy)
├── sim/            # Python simulation engine
├── front/          # JavaScript/React frontend (TypeScript + Vite)
├── scripts/        # Development utilities
├── .github/        # CI/CD workflows
└── admin/          # Administrative documents
```

### Code Quality Standards

**Python (Backend & Simulation):**

- Testing: pytest with coverage
- Linting: flake8, mypy
- Formatting: black (88 char line length)

**JavaScript/TypeScript (Frontend):**

- Testing: Vitest with @testing-library/react
- Linting: ESLint
- Formatting: Prettier
- Type Checking: TypeScript strict mode

### Branch Naming Convention

Format: `[prefix]/[issue-number]-[description]`

**Prefixes:**

- `feature/` - New features
- `bugfix/` - Bug fixes
- `ci/` - CI/CD changes
- `docs/` - Documentation

### Coverage Reports

Local HTML coverage reports:

- **Python**: `coverage_html/index.html`
- **Frontend**: `front/coverage/index.html`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
