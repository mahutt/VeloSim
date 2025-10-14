# VeloSim Logging System

Centralized logging infrastructure using **Grafana**, **Loki**, and **Promtail** for the VeloSim project.

## 🏗️ Architecture

### Components

- **Grafana** (Port 3000): Web UI for log visualization and querying
- **Loki** (Port 3100): Log aggregation and storage backend
- **Promtail**: Scrapes logs from files and ships them to Loki
- **Logger Module**: Python API for structured logging across all components

## 🚀 Quick Start

### 1. Start the Logging Stack

```bash
# Start all services (Grafana, Loki, Promtail, PostgreSQL)
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Use the Logger in Your Code

```python
from back.grafana_logging.logger import get_logger

# Create a logger for your module
logger = get_logger(__name__)

# Log at different levels
logger.debug("Debugging information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue!")
```

### 3. View Logs in Grafana

1. Open http://localhost:3000 (username: `admin`, password: `admin`)
2. Navigate to **Explore** (compass icon)
3. Select **Loki** datasource
4. Query: `{job="python_app"}`

## 📚 Usage Guide

### Backend (FastAPI) Logging

```python
from back.grafana_logging.logger import get_logger

logger = get_logger(__name__)

@app.get("/api/v1/stations")
async def get_stations():
    logger.info("Fetching all stations")
    try:
        stations = await station_service.get_all()
        logger.info(f"Retrieved {len(stations)} stations")
        return stations
    except Exception as e:
        logger.error(f"Failed to fetch stations: {e}", exc_info=True)
        raise
```

### Simulator Logging

```python
from back.grafana_logging.logger import get_logger

logger = get_logger("simulator")

def run_simulation(config):
    logger.info(f"Starting simulation with config: {config}")

    for step in range(config.max_steps):
        logger.debug(f"Simulation step {step}")
        # ... simulation logic ...

    logger.info("Simulation completed successfully")
```

### Frontend Logging (via API)

Create a logging endpoint in rhe FastAPI backend:

```python
from fastapi import APIRouter, Body
from back.grafana_logging.logger import get_logger

router = APIRouter()
frontend_logger = get_logger("frontend")

@router.post("/api/v1/logs")
async def log_from_frontend(
    level: str = Body(...),
    message: str = Body(...),
    context: dict = Body(None)
):
    """Receive logs from frontend and log them server-side."""
    log_func = getattr(frontend_logger, level.lower(), frontend_logger.info)

    if context:
        log_func(f"[Frontend] {message}", extra={"context": context})
    else:
        log_func(f"[Frontend] {message}")

    return {"status": "logged"}
```

Frontend usage (JavaScript/TypeScript):

```typescript
// utils/logger.ts
export const logger = {
  info: (message: string, context?: any) => {
    fetch("/api/v1/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: "info", message, context }),
    });
  },
  error: (message: string, context?: any) => {
    fetch("/api/v1/logs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: "error", message, context }),
    });
  },
};

// Usage in React components
logger.info("User logged in", { userId: user.id });
logger.error("Failed to load data", { endpoint: "/api/stations" });
```

## 🔧 Configuration

### Log Format

The logger uses **different formats** for file vs console output:

- **File format**: `module - LEVEL - message`
  _(No timestamp - Loki adds it automatically to avoid duplication in Grafana)_
- **Console format**: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`
  _(With timestamp for local debugging)_

### Log Levels

The logger supports standard Python logging levels:

- `DEBUG` (10): Detailed diagnostic information
- `INFO` (20): General informational messages
- `WARNING` (30): Warning messages
- `ERROR` (40): Error messages
- `CRITICAL` (50): Critical issues

### Environment Variables

Configure logging behavior with these environment variables in your `.env` file:

| Variable         | Description                 | Default Value                   | Options                                         |
| ---------------- | --------------------------- | ------------------------------- | ----------------------------------------------- |
| `LOG_LEVEL`      | Minimum log level to record | `INFO`                          | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_TO_FILE`    | Enable writing logs to file | `true`                          | `true`, `false`                                 |
| `LOG_TO_CONSOLE` | Enable console output       | `true`                          | `true`, `false`                                 |
| `LOG_FILE_PATH`  | Path to log file            | `back/grafana_logging/logs.txt` | Any valid file path                             |

## 📊 Grafana Queries

### Basic Queries

```logql
# All Python application logs
{job="python_app"}

# Filter by log level
{job="python_app"} |= "ERROR"
{job="python_app"} |= "WARNING"

# Frontend logs only
{job="python_app"} |= "[Frontend]"

# Simulator logs
{job="python_app"} |~ "simulator"

# Logs from specific module
{job="python_app"} |= "back.api.v1"

# Rate of errors per minute
rate({job="python_app"} |= "ERROR" [1m])
```
