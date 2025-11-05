import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';
import { mockDisplayError, MockMap } from './mocks';

// We mock useError to prevent actual error dialogs during tests - global error handling tests are in error-provider.test.tsx
vi.mock('~/hooks/use-error', () => {
  return {
    default: () => ({
      displayError: mockDisplayError,
    }),
  };
});

vi.mock(import('~/lib/logger'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    log: vi.fn(),
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
