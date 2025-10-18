<div align="center">

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Node.js-18%2B-green?logo=node.js&logoColor=white" alt="Node.js Version">
  <img src="https://github.com/vinishamanek/VeloSim/actions/workflows/main-ci.yml/badge.svg?branch=main" alt="Build">
  <img src="https://codecov.io/gh/vinishamanek/VeloSim/branch/main/graph/badge.svg?token=4GVZ2O1N5U" alt="Total Coverage">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style">
</p>

<img style="height: 6em;" src="TeamLogo.png" alt="TeamLogo"/>

</div>

# VeloSim

**VeloSim** is an open-source network simulation platform that enables job dispatchers to manage distributed resources in dynamic environments, built with a Python backend/simulation engine and a modern JavaScript frontend.

## Project Structure

```
VeloSim/
├── back/           # Python backend API
├── sim/            # Python simulation engine
├── front/          # JavaScript/React frontend
├── scripts/        # Development utilities
├── .github/        # CI/CD workflows
└── admin/          # Administrative documents
```

## Quick Start

### Prerequisites

- Python 3.11 with pip
- Node.js 18+ with npm
- Git

### Setup

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
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

3. **Setup the project:**

   ```bash
   # Option A: Use npm script (installs everything)
   npm run setup

   # Option B: Manual setup
   pip install -e .[dev]           # Install Python dependencies
   pre-commit install              # Setup pre-commit hooks
   cd front && npm install && cd.. # Install frontend dependencies
   ```

   The setup will automatically:

   - Install Python dependencies with development tools
   - Configure pre-commit hooks for code quality
   - Install frontend dependencies

### Development Commands

> **Note:** If using a virtual environment, make sure to activate it first:
> Windows: `.venv\Scripts\activate` | macOS/Linux: `source .venv/bin/activate`

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

## Code Quality & Standards

### Python (Backend & Simulation)

- **Testing**: pytest with coverage reporting
- **Linting**: flake8 for style, mypy for type checking
- **Formatting**: black with 88 character line length
- **Coverage**: HTML reports generated in `coverage_html/`

### JavaScript/TypeScript (Frontend)

- **Testing**: Vitest with @testing-library/react for component testing
- **Linting**: ESLint with TypeScript and React rules
- **Formatting**: Prettier for consistent code style
- **Type Checking**: TypeScript with strict configuration
- **Coverage**: HTML reports generated in `front/coverage/`
- **Build Tool**: Vite with React Router for SSR capabilities

### Git Workflow

#### Pre-commit Hooks

The project uses pre-commit hooks that automatically run on each commit:

- **Code formatting**: black (Python), prettier (JavaScript)
- **Linting**: flake8, mypy (Python), ESLint (JavaScript)
- **Basic checks**: trailing whitespace, file endings, merge conflicts
- **Commit message validation**: Angular convention + issue number requirement

#### Commit Message Format

```
type(scope): description #123

Examples:
- feat: add user authentication #456
- fix: resolve login bug fixes #789
- docs: update API documentation closes #101
- refactor: improve performance resolves #234
```

**Required patterns for issue numbers:**

- `#123` (direct reference)
- `fixes #123`, `closes #123`, `resolves #123`
- Case insensitive variations

#### Branch Naming Convention

All branches must follow the structured naming convention:

**Format:** `[prefix]/[issue-number]-[hyphen-separated-name]`

**Branch Prefixes:**

- `feature/` - New features and enhancements
- `bugfix/` - Bug fixes and patches
- `ci/` - CI/CD and infrastructure changes
- `docs/` - Documentation only changes

**Examples:**

```bash
git checkout -b feature/123-user-authentication
git checkout -b bugfix/456-fix-memory-leak
git checkout -b ci/789-add-coverage-checks
git checkout -b docs/101-update-api-documentation
```

#### CI/CD Pipeline

- **Backend CI** (`backend-ci.yml`) - Runs when:
  - `back/` directory files change
  - `pyproject.toml` changes
  - Backend CI workflow file changes
- **Frontend CI** (`frontend-ci.yml`) - Runs when:
  - `front/` directory files change
  - Frontend CI workflow file changes
- **Simulation CI** (`simulation-ci.yml`) - Runs when:
  - `sim/` directory files change
  - Simulation CI workflow file changes
- **License Validation** - Runs when:
  - Source files (`.py`, `.js`, `.jsx`, `.ts`, `.tsx`) change

## Development Workflow

1. **Create a feature branch** with proper naming:

   ```bash
   git checkout -b feature/awesome-feature    # For new features
   git checkout -b bugfix/fix-critical-bug    # For bug fixes
   git checkout -b ci/improve-workflows       # For CI changes
   git checkout -b docs/update-api-docs       # For documentation
   ```

2. **Make changes** following the code standards
3. **Write tests** for new functionality
4. **Run tests locally**: `npm run test`
5. **Check linting**: `npm run lint`
6. **Commit with proper message**: Include issue number
7. **Push and create PR** - CI will automatically run
8. **Review coverage reports**: Check `coverage_html/` (Python) and `front/coverage/` (JavaScript)

## Coverage Reports

Local HTML coverage reports are generated and gitignored:

- **Python**: `coverage_html/index.html`
- **Frontend**: `front/coverage/index.html`

Open these files in a browser to view detailed coverage information.

## Troubleshooting

### Pre-commit Issues

```bash
# Reinstall hooks
pre-commit clean
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Contributing

1. Ensure all tests pass locally
2. Follow the established code style (enforced by pre-commit)
3. Include tests for new features
4. Use descriptive commit messages with issue numbers
5. Keep PRs focused and atomic

## 📚 Documentation Links

- **[Backend Documentation](back/DEVELOPMENT.md)**
- **[Frontend Documentation](front/README.md)**
- **[Simulation Documentation](sim/README.md)**

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
