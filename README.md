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

> **Windows users:** Ensure your `.env` file includes `LOG_TO_LOKI=false`. The Loki
> container is not started by `dev:services`, and on Windows, failed DNS resolution
> for the Docker-internal Loki hostname blocks the backend event loop, causing
> requests to hang for minutes.

**Quick start with npm:**

```bash
# Start everything (PostgreSQL, GraphHopper, Backend, Frontend)
npm run dev

# Or start individual components:
npm run dev:services    # Start Docker services (PostgreSQL + GraphHopper)
npm run dev:backend     # Start backend API
npm run dev:frontend    # Start frontend
```

**Using Docker Compose:**

```bash
# Start all services in containers
docker-compose up -d

# Stop all services
docker-compose down
```

**Ports:**

| Service     | Local Dev (`npm run dev`) | Docker Compose  |
| ----------- | ------------------------- | --------------- |
| Frontend    | 5173                      | 3000            |
| Backend API | 8000                      | 8000            |
| PostgreSQL  | 5433                      | 5432 (internal) |
| GraphHopper | 8989                      | 8989 (internal) |
| Grafana     | N/A                       | 3001            |

> **Note:** `npm run setup` installs Python dependencies locally for IDE autocomplete and running linters/tests. When using Docker Compose, dependencies are automatically installed in containers.

**Testing and linting:**

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

**Documentation:**

```bash
# Generate HTML documentation from docstrings
python scripts/build_docs.py

# Documentation will be available at docs/_build/html/index.html
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

   ```text
   feat: add user authentication #123
   fix: resolve login bug fixes #456
   ```

6. **Push and create PR** - CI will automatically run

### Project Structure

```plaintext
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

## 🚢 Deploying to Production

VeloSim deploys via Ansible to any Ubuntu 24.04 server.

**Prerequisites:** A server with SSH access and an SSH key pair for GitHub Actions.

```bash
# 1. Generate a deploy key
ssh-keygen -t ed25519 -C "deploy@github-actions" -f ansible_deploy_key

# 2. Configure your deployment
cp ansible/group_vars/all.yml.example ansible/group_vars/all.yml  # edit with your values
# Update ansible/inventories/production with your server IP

# 3. Add GitHub Secrets:
#    DEPLOY_SSH_KEY      — contents of ansible_deploy_key (private)
#    DEPLOY_HOST         — your server IP or hostname
#    DEPLOY_HOST_KEY     — from: ssh-keyscan -t ed25519 YOUR_SERVER_IP
#    DEPLOY_USER         — deploy user (default: github)
#    POSTGRES_PASSWORD   — database password
#    DOMAIN_NAME         — your domain (e.g. yourdomain.com)
#    VITE_MAPBOX_ACCESS_TOKEN — optional, for map features

# 4. Run initial provisioning (sets up server from scratch)
cd ansible && ansible-playbook -i inventories/production deploy.yml -u root

# Subsequent deploys run automatically on push to main, or manually via GitHub Actions.
```

See [`ansible/README.md`](ansible/README.md) for full details including backup, SSL, and recovery.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
