import { reactRouter } from '@react-router/dev/vite';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import tsconfigPaths from 'vite-tsconfig-paths';
import { coverageConfigDefaults } from 'vitest/config';

export default defineConfig(({ mode }) => {
  // Load env from root directory (one level up from front/)
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '');

  return {
    plugins: [
      tailwindcss(),
      !process.env.VITEST && reactRouter(),
      tsconfigPaths(),
    ],
    define: {
      // Expose specific env variables to the client with VITE_ prefix
      'import.meta.env.VITE_MAPBOX_ACCESS_TOKEN': JSON.stringify(
        env.VITE_MAPBOX_ACCESS_TOKEN || env.MAPBOX_ACCESS_TOKEN || ''
      ),
      'import.meta.env.VITE_BACKEND_URL': JSON.stringify(
        env.VITE_BACKEND_URL || env.BACKEND_URL || 'http://localhost:8000'
      ),
    },
    server: {
      proxy: {
        '/api': {
          target: env.BACKEND_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    test: {
      globals: true,
      setupFiles: 'tests/setup',
      environment: 'happy-dom',
      exclude: ['**/e2e/**', '**/node_modules/**'],
      coverage: {
        enabled: true,
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
        reportsDirectory: './coverage',
        thresholds: {
          lines: 90,
          functions: 90,
          branches: 90,
          statements: 90,
        },
        include: ['app/**'],
        exclude: [
          'app/root.tsx',
          'app/routes.ts',
          ...coverageConfigDefaults.exclude,
        ],
      },
    },
  };
});
