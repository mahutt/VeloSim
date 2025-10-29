import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';
import { MockMap } from './mocks';

// We mock useError to prevent actual error dialogs during tests - global error handling tests are in error-provider.test.tsx
vi.mock('~/hooks/use-error', () => {
  return {
    default: () => ({
      displayError: () => {
        // No-op for testing
      },
    }),
  };
});

vi.mock('mapbox-gl', () => {
  return {
    default: {
      Map: MockMap,
    },
  };
});

beforeEach(async () => {
  MockMap.clear();
});
