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

import { expect, test, vi, beforeEach, it, describe } from 'vitest';
import { render, screen } from '@testing-library/react';
import Simulation, {
  meta,
  getContainerWidth,
} from '~/routes/simulations/simulation';
import { createRoutesStub } from 'react-router';
import type { MapContextType } from '~/providers/map-provider';

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
const { mockUseMap } = vi.hoisted(() => {
  return {
    mockUseMap: {
      mapRef: { current: null },
      mapContainerRef: { current: null },
      mapLoaded: false,
    } as MapContextType,
  };
});
vi.mock('~/providers/map-provider', () => ({
  useMap: (): MapContextType => mockUseMap,
  MapProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

const { mockUseSimulation } = await vi.hoisted(async () => {
  const { makeSimulationContext, makeReactiveSimulationState } =
    await import('tests/test-helpers');
  return {
    mockUseSimulation: makeSimulationContext({
      state: makeReactiveSimulationState({ isLoading: false }),
    }),
  };
});

vi.mock('~/providers/simulation-provider', () => ({
  SimulationProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  useSimulation: () => mockUseSimulation,
}));

vi.mock('~/providers/task-assignment-provider', () => ({
  TaskAssignmentProvider: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

// Temporary mock to activate the scrubber for testing purposes:
vi.mock('~/hooks/use-feature', () => ({
  default: (flag: string) => {
    if (flag === 'simulationScrubber') return true;
    return false;
  },
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
      path: '/simulations/:sim_id',
      Component: Simulation,
    },
  ]);

  render(<Stub initialEntries={['/simulations/sim-id']} />);
  expect(screen.getByTestId('map-container')).toBeInTheDocument();
});

test('simulation page simulation provider and simulation UI elements when map is ready', async () => {
  mockUseMap.mapLoaded = true;
  mockUseMap.mapRef.current = {} as unknown as mapboxgl.Map;
  const Stub = createRoutesStub([
    {
      path: '/simulations/:sim_id',
      Component: Simulation,
    },
  ]);

  render(<Stub initialEntries={['/simulations/sim-id']} />);
  expect(screen.getByText('Resource Bar')).toBeInTheDocument();
  expect(screen.getByText('Playback Controls')).toBeInTheDocument();
  expect(screen.getByText('Selected Item Bar')).toBeInTheDocument();
});

test('simulation page renders loader while simulation engine is loading', async () => {
  mockUseMap.mapLoaded = true;
  mockUseMap.mapRef.current = {} as unknown as mapboxgl.Map;
  mockUseSimulation.state.isLoading = true;
  const Stub = createRoutesStub([
    {
      path: '/simulations/:sim_id',
      Component: Simulation,
    },
  ]);

  render(<Stub initialEntries={['/simulations/sim-id']} />);
  // assert NO UI elements are shown while loading
  expect(screen.queryByText('Resource Bar')).not.toBeInTheDocument();
  expect(screen.queryByText('Playback Controls')).not.toBeInTheDocument();
  expect(screen.queryByText('Selected Item Bar')).not.toBeInTheDocument();
  // assert loader is shown
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
});

test('simulation page renders nothing if sim_id is missing', async () => {
  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulation,
    },
  ]);

  render(<Stub initialEntries={['/simulations']} />);
  expect(screen.queryByText('Resource Bar')).not.toBeInTheDocument();
  expect(screen.queryByText('Playback Controls')).not.toBeInTheDocument();
  expect(screen.queryByText('Selected Item Bar')).not.toBeInTheDocument();
  expect(screen.queryByText('Map Container')).not.toBeInTheDocument();
});

describe('getContainerWidth', () => {
  it('returns correct width for single digit day', () => {
    expect(getContainerWidth(5)).toBe('w-[260px]');
  });

  it('returns correct width for double digit day', () => {
    expect(getContainerWidth(15)).toBe('w-[268px]');
  });

  it('returns correct width for triple digit day', () => {
    expect(getContainerWidth(150)).toBe('w-[277px]');
  });
});
