import { reactRouter } from '@react-router/dev/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import tsconfigPaths from 'vite-tsconfig-paths';
import { coverageConfigDefaults } from 'vitest/config';

export default defineConfig({
  plugins: [
    tailwindcss(),
    !process.env.VITEST && reactRouter(),
    tsconfigPaths(),
  ],
  test: {
    globals: true,
    setupFiles: 'tests/setup',
    environment: 'happy-dom',
    coverage: {
      enabled: true,
      provider: 'v8',
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
      include: ['app/**'],
      exclude: [
        'app/root.tsx',
        'app/routes.ts',
        ...coverageConfigDefaults.exclude,
      ],
    },
  },
});
