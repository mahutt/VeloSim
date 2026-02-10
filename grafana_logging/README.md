# VeloSim Logging System

Centralized logging and monitoring infrastructure using **Grafana**, **Loki**, **Alloy**, and **Prometheus** for the VeloSim project.

## 🏗️ Architecture

### Components

**Logging Stack:**
- **Grafana** (Port 3001): Web UI for log visualization, querying, and metrics dashboards
- **Loki** (Port 3100): Log aggregation and storage backend
- **Alloy** (Port 12345): Scrapes logs from files and ships them to Loki (UI at http://localhost:12345)
- **Logger Module**: Python API for structured logging across all components

**Monitoring Stack:**
- **Prometheus** (Port 9090): Metrics collection and time-series database
- **Python Backend Metrics**: Process-level metrics (CPU, RAM usage) via `prometheus_client`

## 🚀 Quick Start

### 1. Start the Logging Stack

```bash
# Start all services (Grafana, Loki, Alloy, PostgreSQL)
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Use the Logger in Your Code

```python
from grafana_logging.logger import get_logger

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

1. Open http://localhost:3001 (username: `admin`, password: `admin`)
2. Navigate to **Explore** (compass icon)
3. Select **Loki** datasource
4. Query: `{job="python_app"}`

## 📚 Usage Guide

### Backend (FastAPI) Logging

```python
from grafana_logging.logger import get_logger

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
from grafana_logging.logger import get_logger

logger = get_logger("simulator")

def run_simulation(config):
    logger.info(f"Starting simulation with config: {config}")

    for step in range(config.max_steps):
        logger.debug(f"Simulation step {step}")
        # ... simulation logic ...

    logger.info("Simulation completed successfully")
```

### Frontend Logging (via API)

Create a logging endpoint in the FastAPI backend:

```python
from fastapi import APIRouter, Body
from grafana_logging.logger import get_logger

router = APIRouter()
frontend_logger = get_logger("frontend")

@router.post("/api/v1/logs/frontend")
async def log_from_frontend(
    level: str = Body(...),
    message: str = Body(...),
    context: dict = Body(None)
):
    """Receive a log from frontend and log them server-side."""
    log_func = getattr(frontend_logger, level.lower(), frontend_logger.info)

    if context:
        log_func(f"[Frontend] {message}", extra={"context": context})
    else:
        log_func(f"[Frontend] {message}")

    return {"status": "logged"}

# Batch endpoint: POST /api/v1/logs/frontend/batch
```

Frontend usage (JavaScript/TypeScript):

```typescript
// utils/logger.ts
export const logger = {
  info: (message: string, context?: any) => {
    fetch("/api/v1/logs/frontend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: "info", message, context }),
    });
  },
  error: (message: string, context?: any) => {
    fetch("/api/v1/logs/frontend", {
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
  _(No timestamp - Loki assigns the ingestion timestamp. Note: this means logs cannot be re-ingested with their original timestamps)_
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
| `LOG_FILE_PATH`  | Path to log file            | `grafana_logging/logs.txt`      | Any valid file path                             |

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

## 🛠️ Developer Guide

### Extending the Monitoring Dashboard

#### Adding New Panels

1. **Via Grafana UI** (Recommended for development):
   - Open http://localhost:3001 and navigate to the dashboard
   - Click "Add" → "Visualization"
   - Select Prometheus datasource
   - Write your query (see examples below)
   - Configure panel options (title, unit, thresholds)
   - Click "Apply" and save the dashboard
   - Export JSON: Dashboard Settings → JSON Model → Copy

2. **Update the provisioned dashboard**:
   - Paste the exported JSON into `grafana/provisioning/dashboards/python-performance.json`
   - Restart Grafana: `docker-compose restart grafana` (or `docker-compose down` followed by `docker compose up -d`)

### Exploring Available Metrics

**Browse all metrics in Grafana**:
1. Navigate to Explore → Prometheus
2. Click "Metrics browser" button
3. Search for:
   - `process_*` - Python process metrics (CPU, memory, file descriptors)
   - `up` - Service health status

**Or query Prometheus directly**:
```bash
# List all available metrics
curl http://localhost:9090/api/v1/label/__name__/values

# Query Python backend memory usage
curl 'http://localhost:9090/api/v1/query?query=process_resident_memory_bytes{job="velosim-backend"}'
```

### File Structure

```
grafana_logging/
├── grafana/
│   └── provisioning/
│       ├── datasources/           # Datasource configurations
│       │   ├── loki.yaml          # Loki datasource
│       │   └── prometheus.yaml    # Prometheus datasource
│       └── dashboards/            # Auto-provisioned dashboards
│           ├── dashboards.yaml    # Dashboard provider config
│           └── python-performance.json  # Performance dashboard
├── loki/                          # Loki data storage
├── prometheus/
│   └── prometheus.yml             # Prometheus scrape config
├── alloy/
│   └── config.alloy               # Alloy log collection config
├── logger.py                      # Python logging module
└── README.md                      # This file
```

### Useful Resources

**Official Documentation:**
- [Grafana Docs](https://grafana.com/docs/grafana/latest/) - Dashboard creation, panels, queries
- [Prometheus Docs](https://prometheus.io/docs/introduction/overview/) - Query language (PromQL), configuration
- [cAdvisor GitHub](https://github.com/google/cadvisor) - Container metrics reference
- [Node Exporter GitHub](https://github.com/prometheus/node_exporter) - Available collectors and metrics
- [Loki Docs](https://grafana.com/docs/loki/latest/) - LogQL query language

**Query Language References:**
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/) - Prometheus query syntax
- [PromQL Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/) - rate(), sum(), avg(), etc.
- [LogQL Docs](https://grafana.com/docs/loki/latest/logql/) - Log query syntax

**Grafana Dashboard Development:**
- [Panel Types](https://grafana.com/docs/grafana/latest/panels-visualizations/) - Time series, gauge, stat, etc.
- [Dashboard JSON Model](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/) - Dashboard structure
- [Provisioning Dashboards](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards) - Auto-load dashboards

**Prometheus Exporters:**
- [Exporters List](https://prometheus.io/docs/instrumenting/exporters/) - Third-party exporters for various services
- [Writing Exporters](https://prometheus.io/docs/instrumenting/writing_exporters/) - Create custom exporters

**Troubleshooting:**
- Check Prometheus targets: http://localhost:9090/targets (all should show "UP")
- Check backend metrics: http://localhost:8000/api/v1/metric/metrics
- View Grafana logs: `docker logs velosim-grafana`
- View Prometheus logs: `docker logs velosim-prometheus`

### Common Development Tasks

**Restart monitoring stack**:
```bash
docker-compose restart grafana prometheus
```

**View real-time logs**:
```bash
docker logs -f velosim-grafana
docker logs -f velosim-prometheus
```

**Reset Grafana (clear all changes)**:
```bash
docker-compose down
rm -rf grafana_logging/grafana_data
docker-compose up -d
```

**Test Prometheus scraping**:
```bash
# Check if target is being scraped
curl http://localhost:9090/api/v1/targets

# Query a specific metric
curl 'http://localhost:9090/api/v1/query?query=up'
```
