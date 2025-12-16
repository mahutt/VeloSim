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

import { expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import Simulation, { meta } from '~/routes/simulation';
import { createRoutesStub } from 'react-router';

// Mock MapContainer component
vi.mock('~/components/map/map-container', () => ({
  default: () => <div data-testid="map-container">Map Container</div>,
}));

// Mock other components
vi.mock('~/components/map/playback-controls', () => ({
  default: () => <div>Playback Controls</div>,
}));

vi.mock('~/components/map/selected-item-bar', () => ({
  default: () => <div>Selected Item Bar</div>,
}));

vi.mock('~/components/resource/resource-bar', () => ({
  default: () => <div>Resource Bar</div>,
}));

// Mock providers to render children without context logic
vi.mock('~/providers/map-provider', () => ({
  MapProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

vi.mock('~/providers/simulation-provider', () => ({
  SimulationProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  useSimulation: () => ({
    isLoading: false,
    simulationStatus: 'ready',
    stationsRef: { current: new Map() },
    driversRef: { current: new Map() },
    resources: [],
    selectedItem: null,
    selectItem: vi.fn(),
    clearSelection: vi.fn(),
    assignTaskToResource: vi.fn(),
    simId: 'test-sim-id',
    isConnected: true,
  }),
}));

vi.mock('~/providers/task-assignment-provider', () => ({
  TaskAssignmentProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('simulation page loads the map container', async () => {
  const Stub = createRoutesStub([
    {
      path: '/simulation',
      Component: Simulation,
    },
  ]);

  render(<Stub initialEntries={['/simulation']} />);
  expect(screen.getByTestId('map-container')).toBeInTheDocument();
});
