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

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  useSimulation,
  type SimulationContextType,
} from '~/providers/simulation-provider';
import SelectedItemBar, {
  SelectedItemType,
  type PopulatedResource,
} from '~/components/map/selected-item-bar';
import { FeatureToggleProvider } from '~/providers/feature-toggle-provider';
import { TaskAssignmentProvider } from '~/providers/task-assignment-provider';
import type { Position } from '~/types';

// Mock the useSimulation hook
vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('SelectedItemBar', () => {
  it('should not render when no item is selected', () => {
    vi.mocked(useSimulation).mockReturnValue({
      speedRef: { current: 1 },
      stationsRef: { current: new Map() },
      driversRef: { current: new Map() },
      resourceBarElement: [],
      selectedItem: null,
      selectItem: vi.fn(),
      clearSelection: vi.fn(),
      assignTask: vi.fn(),
      unassignTask: vi.fn(),
      reassignTask: vi.fn(),
      simId: null,
      isConnected: false,
      simulationStatus: 'idle',
      isLoading: false,
      formattedSimTime: null,
      currentDay: 1,
    });

    const { container } = render(
      <FeatureToggleProvider>
        <TaskAssignmentProvider>
          <SelectedItemBar />
        </TaskAssignmentProvider>
      </FeatureToggleProvider>
    );
    expect(container.firstChild).toBeNull();
  });

  it('should render station information when station is selected', () => {
    const mockStation = {
      id: 1,
      name: 'Test Station',
      position: [-73.57776, 45.48944] as Position,
      tasks: [],
    };

    const clearSelectionMock = vi.fn();

    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Station,
        value: mockStation,
      },
      clearSelection: clearSelectionMock,
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      driversRef: { current: new Map() },
      resources: [],
      assignTask: vi.fn(),
      unassignTask: vi.fn(),
      reassignTask: vi.fn(),
      simId: null,
      isConnected: false,
      startSimulation: vi.fn(),
      simulationStatus: 'idle',
      formattedSimTime: null,
      currentDay: 1,
    });

    render(
      <FeatureToggleProvider>
        <TaskAssignmentProvider>
          <SelectedItemBar />
        </TaskAssignmentProvider>
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Station')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('Test Station')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Position')).toBeInTheDocument();
    expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
  });

  it('should render resource information when resource is selected', () => {
    const mockResource: PopulatedResource = {
      id: 5,
      position: [-73.58, 45.49] as Position,
      tasks: [
        { id: 1, stationId: 1, state: 'open', assignedDriverId: null },
        { id: 2, stationId: 2, state: 'open', assignedDriverId: null },
        { id: 3, stationId: 3, state: 'open', assignedDriverId: null },
      ],
      route: {
        coordinates: [
          [-73.58, 45.49],
          [-73.57, 45.5],
        ] as Position[],
      },
      inProgressTask: null,
    };

    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Driver,
        value: mockResource,
      },
      clearSelection: vi.fn(),
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      driversRef: { current: new Map() },
      resourceBarElement: [],
      assignTask: vi.fn(),
      unassignTask: vi.fn(),
      reassignTask: vi.fn(),
      simId: null,
      isConnected: false,
      startSimulation: vi.fn(),
      simulationStatus: 'idle',
      formattedSimTime: null,
      currentDay: 1,
      speedRef: { current: 1 },
      isLoading: false,
    } as SimulationContextType);

    render(
      <FeatureToggleProvider>
        <TaskAssignmentProvider>
          <SelectedItemBar />
        </TaskAssignmentProvider>
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Driver')).toBeInTheDocument();
    expect(screen.getByText('#5')).toBeInTheDocument();
    expect(screen.getByText('Position')).toBeInTheDocument();
    expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
    expect(screen.getByText('Task #1')).toBeInTheDocument();
    expect(screen.getByText('Task #2')).toBeInTheDocument();
    expect(screen.getByText('Task #3')).toBeInTheDocument();
  });

  it('should call clearSelection when close button is clicked', async () => {
    const user = userEvent.setup();
    const clearSelectionMock = vi.fn();

    const mockStation = {
      id: 1,
      name: 'Test Station',
      position: [-73.57776, 45.48944] as Position,
      tasks: [],
    };

    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Station,
        value: mockStation,
      },
      clearSelection: clearSelectionMock,
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      driversRef: { current: new Map() },
      resources: [],
      assignTask: vi.fn(),
      unassignTask: vi.fn(),
      reassignTask: vi.fn(),
      simId: null,
      isConnected: false,
      startSimulation: vi.fn(),
      simulationStatus: 'idle',
      formattedSimTime: null,
      currentDay: 1,
    });

    render(
      <FeatureToggleProvider>
        <TaskAssignmentProvider>
          <SelectedItemBar />
        </TaskAssignmentProvider>
      </FeatureToggleProvider>
    );

    const closeButton = screen.getByRole('button');
    await user.click(closeButton);

    expect(clearSelectionMock).toHaveBeenCalledTimes(1);
  });

  it('should display tasks when station has tasks', () => {
    const mockStation = {
      id: 1,
      name: 'Test Station',
      position: [-73.57776, 45.48944] as Position,
      tasks: [
        { id: 1, stationId: 1, type: 'battery_swap' as const },
        { id: 2, stationId: 1, type: 'battery_swap' as const },
      ],
    };

    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Station,
        value: mockStation,
      },
      clearSelection: vi.fn(),
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      driversRef: { current: new Map() },
      resources: [],
      tasks: [],
      assignTask: vi.fn(),
      unassignTask: vi.fn(),
      reassignTask: vi.fn(),
      simId: null,
      isConnected: false,
      startSimulation: vi.fn(),
      simulationStatus: 'idle',
      formattedSimTime: null,
      currentDay: 1,
    });

    render(
      <FeatureToggleProvider>
        <TaskAssignmentProvider>
          <SelectedItemBar />
        </TaskAssignmentProvider>
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
    const taskItems = screen.getAllByText(/^Task #/);
    expect(taskItems).toHaveLength(2);
  });
});
