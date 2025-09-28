import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';
import { MockMap } from './mocks';

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
