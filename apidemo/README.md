# VeloSim API Demo - Automated Task Dispatcher

Automated task dispatching for VeloSim using the REST API. Implements a simple greedy algorithm that continuously assigns open tasks to idle drivers.

## Quick Start

```bash
cd apidemo
./setup.sh
source venv/bin/activate
python dispatcher.py
```

## Prerequisites

- Python 3.10+
- VeloSim backend running or deployed
- Valid user credentials
- A simulation with tasks

## Setup

### Automated Setup

```bash
./setup.sh
```

This will:
1. Create virtual environment
2. Install dependencies (`requests`, `openapi-python-client`)
3. Generate Python client from local OpenAPI spec backup

### Manual Setup

```bash
pip install -r requirements.txt
python generate_client.py --local
```

## Running the Dispatcher

```bash
python dispatcher.py
```

You'll be prompted for:
- **API URL** (default: `http://localhost:8000`)
- **Username**
- **Password**
- **Simulation ID** (UUID)

The dispatcher will continuously assign nearest tasks to idle drivers until stopped (Ctrl+C) or the simulation completes.

## Algorithm

Greedy nearest-neighbor approach:
1. Fetch all `OPEN` tasks and `IDLE` drivers
2. For each idle driver, assign the nearest open task (by station location)
3. Wait 2 seconds
4. Repeat

## Environment Variables

Skip interactive prompts by setting:

```bash
export VELOSIM_API_URL="http://localhost:8000"
export VELOSIM_USERNAME="your-username"
export VELOSIM_PASSWORD="your-password"
export VELOSIM_SIM_ID="your-simulation-uuid"
export POLL_INTERVAL="2.0"

python dispatcher.py
```

## Regenerating the Client

By default, `setup.sh` uses the committed `openapi.json` backup. To regenerate from a running backend:

```bash
python generate_client.py http://localhost:8000
```

**Note**: Production deployments (velosim.app) have OpenAPI docs disabled for security.

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/token` | OAuth2 authentication |
| `GET /api/v1/simulation/{sim_id}/tasks` | List tasks |
| `GET /api/v1/simulation/{sim_id}/drivers` | List drivers |
| `POST /api/v1/simulation/{sim_id}/drivers/assign` | Assign task to driver |

## Troubleshooting

**Connection failed**: Verify backend is running and URL is correct

**Authentication failed**: Check username/password and user is enabled

**No tasks assigned**: Ensure simulation is running with OPEN tasks and IDLE drivers

**Client generation failed**: Use `--local` flag for production deployments

## Customizing the Algorithm

Modify `find_nearest_task()` in `dispatcher.py` to implement different assignment strategies (e.g., priority-based, load balancing, etc.).
