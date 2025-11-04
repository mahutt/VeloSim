# VeloSim Front-End

## Environment variables

Below is a list of secrets that should be defined in a `.env.local` file at the root of the `/front` directory. For each variable, instructions are provided on how to obtain / set a valid value.

- `VITE_MAPBOX_ACCESS_TOKEN`
  - Visit the [Mapbox console](https://console.mapbox.com/) - you may need to sign in or create an account. In the top right corner of the home page, you'll find a "Default public token" section. Use the token provided there.
- `VITE_BACKEND_URL`
  - Set this environment variable to `http://localhost:8000` for development.

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
