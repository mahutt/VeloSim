# VeloSim Simulation Engine

This directory contains the VeloSim simulation engine that powers the bike-sharing network simulations.

## Routing Configuration

The simulation engine uses GraphHopper for traffic-aware routing with per-request custom-model speed adjustments.

### Environment Variables

Set the GraphHopper server URL:

```bash
export GRAPHHOPPER_URL=http://localhost:8989
export GRAPHHOPPER_TIMEOUT=20
```

Or add to your `.env` file:

```bash
GRAPHHOPPER_URL=http://localhost:8989
GRAPHHOPPER_TIMEOUT=20
DATABASE_URL=postgresql://velosim:velosim@localhost:5433/velosim
```

**Configuration Options:**

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPHHOPPER_URL` | GraphHopper server URL | `http://localhost:8989` |
| `GRAPHHOPPER_TIMEOUT` | Request timeout in seconds (for long routes or slow networks) | `20` |

### Running Local GraphHopper Server

```bash
# Start with npm (recommended)
npm run dev:services

# Or prepare data and start GraphHopper (first time)
npm run graphhopper:prepare

# Start existing GraphHopper instance
npm run graphhopper:up

# View logs
npm run graphhopper:logs

# Stop GraphHopper
npm run graphhopper:down
```

## Testing

Run the routing test script to verify GraphHopper connectivity:

```bash
npm run routingTest
```

This will calculate a test route and generate detailed output in `route_output.txt`.
