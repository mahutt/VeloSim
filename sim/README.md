# VeloSim Simulation Engine

This directory contains the VeloSim simulation engine that powers the bike-sharing network simulations.

## OSRM Configuration

The simulation engine uses OSRM (Open Source Routing Machine) for routing calculations.

### Environment Variable

Set the OSRM server URL:

```bash
export OSRM_URL=http://localhost:5001
```

Or add it to your `.env` file in the project root:

```bash
OSRM_URL=http://localhost:5001
DATABASE_URL=postgresql://velosim:velosim@localhost:5433/velosim
```

### Running Local OSRM Server

```bash
# Start with npm (recommended)
npm run dev:services

# Or use docker-compose directly
docker-compose up -d osrm postgres
```

## Testing

Run the routing test script to verify OSRM connectivity:

```bash
npm run routingTest
```

This will calculate a test route and generate detailed output in `route_output.txt`.
