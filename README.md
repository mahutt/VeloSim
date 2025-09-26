<div align="center">

<img style="height: 6em;" src="TeamLogo.png" alt="TeamLogo"/>

</div>

# VeloSim

**VeloSim** is a simulation platform with a Python backend/simulation engine and a modern JavaScript frontend.

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
# Install all dependencies
npm run install:all

# Run all tests
npm run test

# Run tests with coverage
npm run test:coverage

# Lint all code
npm run lint

# Format all code
npm run format

# Build frontend
npm run build

# Start frontend development server
npm run dev:frontend
```

## Code Quality & Standards

### Python (Backend & Simulation)

- **Testing**: pytest with coverage reporting
- **Linting**: flake8 for style, mypy for type checking
- **Formatting**: black with 88 character line length
- **Coverage**: HTML reports generated in `coverage_html/` (gitignored)

### JavaScript/TypeScript (Frontend)

- **Testing**: Vitest with @testing-library/react for component testing
- **Linting**: ESLint with TypeScript and React rules
- **Formatting**: Prettier for consistent code style
- **Type Checking**: TypeScript with strict configuration
- **Coverage**: HTML reports generated in `front/coverage/` (gitignored)
- **Build Tool**: Vite with React Router for SSR capabilities

### Git Workflow

#### Pre-commit Hooks

The project uses pre-commit hooks that automatically run on each commit:

- **Code formatting**: black (Python), prettier (JavaScript)
- **Linting**: flake8, mypy (Python), ESLint (JavaScript)
- **Basic checks**: trailing whitespace, file endings, merge conflicts
- **Commit message validation**: Angular convention + issue number requirement

#### Commit Message Format

Follow Angular commit convention with required issue number:

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

All branches must follow one of these naming conventions:

**Branch Prefixes:**

- `feature/` - New features and enhancements
- `bugfix/` - Bug fixes and patches
- `ci/` - CI/CD and infrastructure changes
- `docs/` - Documentation only changes

Examples:

```bash
git checkout -b feature/user-authentication
git checkout -b bugfix/fix-memory-leak
git checkout -b ci/add-coverage-checks
git checkout -b docs/update-readme
```

#### Smart CI/CD Pipeline

GitHub Actions run **intelligently** based on **changed files**, not branch names:

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
  - Only for `feature/` and `bugfix/` branches

**Benefits:**

- ✅ No unnecessary CI runs
- ✅ Faster feedback on relevant changes only
- ✅ Efficient resource usage

## Development Workflow

1. **Create a feature branch** with proper naming:

   ```bash
   git checkout -b feature/awesome-feature    # For new features
   git checkout -b bugfix/fix-critical-bug    # For bug fixes
   git checkout -b ci/improve-workflows       # For CI changes
   git checkout -b docs/update-api-docs       # For documentation
   ```

   git checkout -b ci/feature-name # For CI/infrastructure
   git checkout -b docs/feature-name # For documentation

   ```

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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
