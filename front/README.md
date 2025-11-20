# VeloSim Front-End

## Environment Variables

Environment variables are configured in the **root `.env` file** (located in the project root, one directory up from `/front`).

**Required Configuration:**

Add these variables to the root `.env` file:

- **`MAPBOX_ACCESS_TOKEN`** (required)
  - Mapbox access token for map rendering
  - Get your token from [Mapbox Console](https://account.mapbox.com/)

- **`BACKEND_URL`** (optional, defaults to `http://localhost:8000`)
  - Backend API URL
  - Use `http://localhost:8000` for local development

The frontend automatically reads these variables from the root `.env` file via `vite.config.ts`.

## Testing

### Unit Tests

Run unit tests with Vitest:

```bash
# Run tests
npm run test
```

### End-to-End Tests

Run e2e Playwright tests.

**First-time setup:**

```bash
npx playwright install
```

**Running tests:**

```bash
# Run all e2e tests
npm run test:e2e

# Run e2e tests with video recording
npm run test:e2e:video
```
