/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { expect, test, vi } from 'vitest';
import { render } from '@testing-library/react';
import MapContainer from '~/components/map/map-container';
import { MapProvider } from '~/providers/map-provider';

// Mock useAuth hook
vi.mock('~/hooks/use-auth', () => ({
  default: () => ({
    user: { id: 1, username: 'test_user', is_admin: false },
    setUser: vi.fn(),
    loading: false,
    setLoading: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    setToken: vi.fn(),
  }),
}));

const { mockServerFrameSource } = await vi.hoisted(() => import('tests/mocks'));
vi.mock('~/lib/frame-sources/server-frame-source', () => {
  return {
    ServerFrameSource: mockServerFrameSource,
  };
});

test('map container render should fail without a map provider', async () => {
  expect(() => {
    render(<MapContainer />);
  }).toThrow('useMap must be used within a MapProvider');
});

test('map container render should succeed with a map provider', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <MapContainer />
    </MapProvider>
  );
  expect(getByTestId('map-container')).toBeDefined();
});
