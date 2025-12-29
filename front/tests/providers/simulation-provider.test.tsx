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

class MockedWebSocketConstructor {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  send = vi.fn();
  close = vi.fn();
}

// Setup global WebSocket mock
global.WebSocket = MockedWebSocketConstructor as unknown as typeof WebSocket;

// Mock the simulation error utils
vi.mock('~/utils/simulation-error-utils', () => ({
  logSimulationError: vi.fn(),
  logMissingEntityError: vi.fn(),
  logFrameProcessingError: vi.fn(),
}));

// Mock useAuth hook with stable user reference
const mockUser = { id: 1, username: 'test_user', is_admin: false };
vi.mock('~/hooks/use-auth', () => ({
  default: () => ({
    user: mockUser,
    setUser: vi.fn(),
    loading: false,
    setLoading: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    setToken: vi.fn(),
  }),
}));

import { expect, test, vi, beforeEach, type Mock } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import { useEffect } from 'react';
import {
  SimulationProvider,
  useSimulation,
} from '~/providers/simulation-provider';
import { MapProvider } from '~/providers/map-provider';
import { TaskAssignmentProvider } from '~/providers/task-assignment-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';
import {
  type BackendPayload,
  type UseSimulationWebSocketOptions,
} from '~/types';
import {
  logSimulationError,
  logMissingEntityError,
} from '~/utils/simulation-error-utils';
import api from '~/api';
import { SelectedItemType } from '~/components/map/selected-item-bar';

// Mock the API module
vi.mock('~/api', () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn().mockResolvedValue({ data: {} }),
    },
  };
});

// Mock the map-helpers module
vi.mock('~/lib/map-helpers.ts', async (importOriginal) => {
  return {
    ...(await importOriginal<typeof import('~/lib/map-helpers.ts')>()),
    loadMapImages: vi.fn(),
    initializeMapSources: vi.fn(),
    setMapLayers: vi.fn(),
    setMapSource: vi.fn(),
    clearRouteDisplay: vi.fn(),
    updateRouteDisplay: vi.fn(),
  };
});

// Mock the map-interactions module
vi.mock('~/lib/map-interactions.ts', () => {
  return {
    setupMapClickHandlers: vi.fn(),
    setupMapHoverHandlers: vi.fn(),
    setupMapDropHandlers: vi.fn(),
  };
});

let wsOptions: UseSimulationWebSocketOptions | null = null;
vi.mock('~/hooks/use-simulation-websocket', () => ({
  useSimulationWebSocket: (opts: UseSimulationWebSocketOptions) => {
    wsOptions = opts;
    return {
      isConnected: true,
      simulationStatus: 'ready',
      wsRef: { current: null },
    };
  },
}));

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Test component to access the simulation context
const TestComponent = () => {
  const { stationsRef, simulationStatus, isConnected } = useSimulation();
  return (
    <div>
      <div data-testid="test-component">
        {stationsRef.current.size > 0 ? 'data-loaded' : 'no-data'}
      </div>
      <div data-testid="status">{simulationStatus}</div>
      <div data-testid="connected">{String(isConnected)}</div>
    </div>
  );
};

// Sample GeoJSON data for testing

// Store references to mocked functions
const mockLogSimulationError = vi.fn();
const mockLogMissingEntityError = vi.fn();

const ClockProbe = () => {
  const { formattedSimTime, currentDay } = useSimulation();
  return (
    <div>
      <div data-testid="time">{formattedSimTime ?? 'null'}</div>
      <div data-testid="day">{currentDay}</div>
    </div>
  );
};

// Mock requestAnimationFrame - prevent infinite recursion by limiting calls
let rafCallCount = 0;
global.requestAnimationFrame = vi.fn((cb) => {
  rafCallCount++;
  // Only execute the first few calls to prevent infinite loops in tests
  if (rafCallCount <= 5) {
    setTimeout(() => cb(performance.now()), 0);
  }
  return rafCallCount;
});
global.cancelAnimationFrame = vi.fn();

// Re-apply mocks before each test since vi.clearAllMocks() clears them
beforeEach(() => {
  vi.clearAllMocks();
  rafCallCount = 0; // Reset RAF call count
  wsOptions = null;

  // Re-apply the simulation error utils mocks
  (logSimulationError as Mock).mockImplementation(mockLogSimulationError);
  (logMissingEntityError as Mock).mockImplementation(mockLogMissingEntityError);
});

test('simulation provider renders without crashing when wrapped in map provider', () => {
  render(
    <MapProvider>
      <SimulationProvider>
        <div data-testid="child">Test Child</div>
      </SimulationProvider>
    </MapProvider>
  );
});

test('simulation provider throws error when used outside of map provider', () => {
  expect(() => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>
    );
  }).toThrow('useMap must be used within a MapProvider');
});

test('useSimulation hook throws error when used outside of simulation provider', () => {
  expect(() => {
    render(
      <MapProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
        </TaskAssignmentProvider>
      </MapProvider>
    );
  }).toThrow('useSimulation must be used within a SimulationProvider');
});

test('simulation provider provides context with initial state', () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  expect(getByTestId('test-component')).toHaveTextContent('no-data');
});

test('clearSelection clears selected item', () => {
  const TestComponentWithSelection = () => {
    const { clearSelection, selectedItem } = useSimulation();
    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? 'item-selected' : 'no-selection'}
        </div>
        <button data-testid="clear-btn" onClick={clearSelection}>
          Clear
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponentWithSelection />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  const clearBtn = getByTestId('clear-btn');
  act(() => {
    clearBtn.click();
  });

  expect(getByTestId('selected-item')).toHaveTextContent('no-selection');
});

test('selectItem selects a station when it exists', async () => {
  const TestComponentWithSelect = () => {
    const { selectItem, selectedItem, stationsRef } = useSimulation();

    // Manually add a station to test selection
    useEffect(() => {
      stationsRef.current.set(1, {
        id: 1,
        name: 'Test Station',
        position: [0, 0],
        taskIds: [],
      });
    }, []);

    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? JSON.stringify(selectedItem.value) : 'none'}
        </div>
        <button
          data-testid="select-btn"
          onClick={() => selectItem(SelectedItemType.Station, 1)}
        >
          Select
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponentWithSelect />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  // Wait for map to be created and trigger load event
  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  // Trigger the map load event to set mapLoaded = true
  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const selectBtn = getByTestId('select-btn');

  await act(async () => {
    selectBtn.click();
  });

  await waitFor(() => {
    const selectedItemText = getByTestId('selected-item').textContent;
    expect(selectedItemText).toContain('Test Station');
  });
});

test('selectItem shows error when station does not exist', async () => {
  const TestComponentWithSelect = () => {
    const { selectItem } = useSimulation();

    return (
      <button
        data-testid="select-missing-btn"
        onClick={() => selectItem(SelectedItemType.Station, 999)}
      >
        Select Missing
      </button>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponentWithSelect />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  // Wait for map to be created and trigger load event
  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  // Trigger the map load event to set mapLoaded = true
  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const selectBtn = getByTestId('select-missing-btn');

  await act(async () => {
    selectBtn.click();
  });

  await waitFor(() => {
    expect(mockLogMissingEntityError).toHaveBeenCalledWith('station', 999);
  });
});

test('selectItem selects a resource when it exists', async () => {
  const TestComponentWithSelect = () => {
    const { selectItem, selectedItem, driversRef } = useSimulation();

    // Manually add a resource to test selection
    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? `resource-${selectedItem.value.id}` : 'none'}
        </div>
        <button
          data-testid="select-btn"
          onClick={() => selectItem(SelectedItemType.Driver, 1)}
        >
          Select
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponentWithSelect />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  // Wait for map to be created and trigger load event
  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  // Trigger the map load event to set mapLoaded = true
  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const selectBtn = getByTestId('select-btn');

  await act(async () => {
    selectBtn.click();
  });

  await waitFor(() => {
    expect(getByTestId('selected-item')).toHaveTextContent('resource-1');
  });
});

test('assignTask posts to API and updates resource taskIds', async () => {
  const TestAssignComponent = () => {
    const { assignTask, driversRef, resourceBarElement } = useSimulation();

    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    const taskCount =
      resourceBarElement.find((r) => r.id === 1)?.taskCount || 0;

    return (
      <div>
        <div data-testid="task-count">{String(taskCount)}</div>
        <button data-testid="assign-btn" onClick={() => assignTask(1, 42)}>
          Assign
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestAssignComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const assignBtn = getByTestId('assign-btn');

  await act(async () => {
    assignBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  expect(api.post).toHaveBeenCalledWith(
    '/simulation/test-sim-123/drivers/assign',
    { task_id: 42, driver_id: 1 }
  );

  await waitFor(() => {
    expect(getByTestId('task-count')).toHaveTextContent('1');
  });
});

test('unassignTask posts to API and removes task from resource', async () => {
  const TestUnassignComponent = () => {
    const { unassignTask, driversRef, resourceBarElement } = useSimulation();

    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [99],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    const taskCount =
      resourceBarElement.find((r) => r.id === 1)?.taskCount || 0;

    return (
      <div>
        <div data-testid="task-count-un">{String(taskCount)}</div>
        <button data-testid="unassign-btn" onClick={() => unassignTask(1, 99)}>
          Unassign
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestUnassignComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const unassignBtn = getByTestId('unassign-btn');

  await act(async () => {
    unassignBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  expect(api.post).toHaveBeenCalledWith(
    '/simulation/test-sim-123/drivers/unassign',
    { task_id: 99, driver_id: 1 }
  );

  await waitFor(() => {
    expect(getByTestId('task-count-un')).toHaveTextContent('0');
  });
});

test('reassignTask posts to API and moves task between resources', async () => {
  const TestReassignComponent = () => {
    const { reassignTask, driversRef, resourceBarElement } = useSimulation();

    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [123],
        inProgressTaskId: null,
        vehicleId: null,
      });
      driversRef.current.set(2, {
        id: 2,
        position: [0, 0],
        taskIds: [],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    const prevCount = resourceBarElement.find((r) => r.id === 1)?.taskCount;
    const newCount = resourceBarElement.find((r) => r.id === 2)?.taskCount;

    return (
      <div>
        <div data-testid="prev-count">{String(prevCount)}</div>
        <div data-testid="new-count">{String(newCount)}</div>
        <button
          data-testid="reassign-btn"
          onClick={() => reassignTask(1, 2, 123)}
        >
          Reassign
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestReassignComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const reassignBtn = getByTestId('reassign-btn');

  await act(async () => {
    reassignBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  expect(api.post).toHaveBeenCalledWith(
    '/simulation/test-sim-123/drivers/reassign',
    { task_id: 123, old_driver_id: 1, new_driver_id: 2 }
  );

  await waitFor(() => {
    expect(getByTestId('prev-count')).toHaveTextContent('0');
    expect(getByTestId('new-count')).toHaveTextContent('1');
  });
});

test('sets clock time and day from initial frame payload', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <ClockProbe />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  await act(async () => {
    wsOptions?.onInitialFrame?.({
      simId: 'test-sim-123',
      clock: {
        simSecondsPassed: 3661,
        simMinutesPassed: 61,
        realSecondsPassed: 3661,
        realMinutesPassed: 61,
        startTime: 0,
      },
      drivers: [],
      vehicles: [],
      stations: [],
      tasks: [],
    } as BackendPayload);
  });

  await waitFor(() => {
    expect(getByTestId('time')).toHaveTextContent('01:01');
    expect(getByTestId('day')).toHaveTextContent('1');
  });
});

test('advances to next day when sim time crosses 24h', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <ClockProbe />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  await act(async () => {
    wsOptions?.onInitialFrame?.({
      simId: 'test-sim-123',
      clock: {
        simSecondsPassed: 86399,
        simMinutesPassed: 1439,
        realSecondsPassed: 86399,
        realMinutesPassed: 1439,
        startTime: 0,
      },
      drivers: [],
      vehicles: [],
      stations: [],
      tasks: [],
    } as BackendPayload);
  });

  await act(async () => {
    wsOptions?.onFrameUpdate?.({
      simId: 'test-sim-123',
      clock: {
        simSecondsPassed: 90061,
        simMinutesPassed: 1501,
        realSecondsPassed: 90061,
        realMinutesPassed: 1501,
        startTime: 0,
      },
      drivers: [],
      vehicles: [],
      stations: [],
      tasks: [],
    } as BackendPayload);
  });

  await waitFor(() => {
    expect(getByTestId('time')).toHaveTextContent('01:01');
    expect(getByTestId('day')).toHaveTextContent('2');
  });
});

test('defaults to 00:00 day 1 for negative sim time', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <ClockProbe />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  await act(async () => {
    wsOptions?.onInitialFrame?.({
      simId: 'test-sim-123',
      clock: {
        simSecondsPassed: -5,
        simMinutesPassed: -1,
        realSecondsPassed: -5,
        realMinutesPassed: -1,
        startTime: 0,
      },
      drivers: [],
      vehicles: [],
      stations: [],
      tasks: [],
    } as BackendPayload);
  });

  await waitFor(() => {
    expect(getByTestId('time')).toHaveTextContent('00:00');
    expect(getByTestId('day')).toHaveTextContent('1');
  });
});

test('displays time correctly with scenario start_time (08:00)', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <ClockProbe />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  await act(async () => {
    wsOptions?.onInitialFrame?.({
      simId: 'test-sim-123',
      clock: {
        simSecondsPassed: 0,
        simMinutesPassed: 0,
        realSecondsPassed: 0,
        realMinutesPassed: 0,
        startTime: 28800,
      },
      drivers: [],
      vehicles: [],
      stations: [],
      tasks: [],
    } as BackendPayload);
  });

  await waitFor(() => {
    expect(getByTestId('time')).toHaveTextContent('08:00');
    expect(getByTestId('day')).toHaveTextContent('1');
  });
});

test('advances time correctly with start_time', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <ClockProbe />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  await act(async () => {
    wsOptions?.onInitialFrame?.({
      simId: 'test-sim-123',
      clock: {
        simSecondsPassed: 7200,
        simMinutesPassed: 120,
        realSecondsPassed: 7200,
        realMinutesPassed: 120,
        startTime: 28800,
      },
      drivers: [],
      vehicles: [],
      stations: [],
      tasks: [],
    } as BackendPayload);
  });

  await waitFor(() => {
    expect(getByTestId('time')).toHaveTextContent('10:00');
    expect(getByTestId('day')).toHaveTextContent('1');
  });
});

test('RAF queue batches multiple rapid selections into single render', async () => {
  const setMapSourceMock = await import('~/lib/map-helpers').then(
    (m) => m.setMapSource
  );
  (setMapSourceMock as Mock).mockClear();

  const TestRapidSelectComponent = () => {
    const { selectItem, stationsRef } = useSimulation();

    useEffect(() => {
      // Add multiple stations
      for (let i = 1; i <= 5; i++) {
        stationsRef.current.set(i, {
          id: i,
          name: `Station ${i}`,
          position: [0, 0],
          taskIds: [],
        });
      }
    }, []);

    return (
      <button
        data-testid="rapid-select-btn"
        onClick={() => {
          // Rapidly select multiple stations
          selectItem(SelectedItemType.Station, 1);
          selectItem(SelectedItemType.Station, 2);
          selectItem(SelectedItemType.Station, 3);
          selectItem(SelectedItemType.Station, 4);
          selectItem(SelectedItemType.Station, 5);
        }}
      >
        Rapid Select
      </button>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestRapidSelectComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  (setMapSourceMock as Mock).mockClear();
  const rapidSelectBtn = getByTestId('rapid-select-btn');

  await act(async () => {
    rapidSelectBtn.click();
    // Wait for RAF to flush
    await new Promise((r) => setTimeout(r, 50));
  });

  // Should batch 5 rapid selections into 1-2 renders (not 5)
  // Exact count depends on RAF timing, but should be significantly less than 5
  const callCount = (setMapSourceMock as Mock).mock.calls.length;
  expect(callCount).toBeLessThan(5);
  expect(callCount).toBeGreaterThan(0);
});

test('RAF queue batches rapid clearSelection calls', async () => {
  const setMapSourceMock = await import('~/lib/map-helpers').then(
    (m) => m.setMapSource
  );
  (setMapSourceMock as Mock).mockClear();

  const TestRapidClearComponent = () => {
    const { clearSelection, stationsRef, selectItem } = useSimulation();

    useEffect(() => {
      stationsRef.current.set(1, {
        id: 1,
        name: 'Station 1',
        position: [0, 0],
        taskIds: [],
      });
    }, []);

    return (
      <div>
        <button
          data-testid="select-first"
          onClick={() => selectItem(SelectedItemType.Station, 1)}
        >
          Select
        </button>
        <button
          data-testid="rapid-clear-btn"
          onClick={() => {
            // Rapidly clear multiple times
            clearSelection();
            clearSelection();
            clearSelection();
            clearSelection();
            clearSelection();
          }}
        >
          Rapid Clear
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestRapidClearComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  // First select a station
  const selectBtn = getByTestId('select-first');
  await act(async () => {
    selectBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  (setMapSourceMock as Mock).mockClear();
  const rapidClearBtn = getByTestId('rapid-clear-btn');

  await act(async () => {
    rapidClearBtn.click();
    // Wait for RAF to flush
    await new Promise((r) => setTimeout(r, 50));
  });

  // Should batch 5 rapid clears into 1-2 renders (not 5)
  const callCount = (setMapSourceMock as Mock).mock.calls.length;
  expect(callCount).toBeLessThan(5);
  expect(callCount).toBeGreaterThan(0);
});

test('RAF queue batches resource selection updates', async () => {
  const setMapSourceMock = await import('~/lib/map-helpers').then(
    (m) => m.setMapSource
  );
  (setMapSourceMock as Mock).mockClear();

  const TestRapidResourceSelectComponent = () => {
    const { selectItem, driversRef } = useSimulation();

    useEffect(() => {
      // Add multiple resources
      for (let i = 1; i <= 5; i++) {
        driversRef.current.set(i, {
          id: i,
          position: [0, 0],
          taskIds: [],
          inProgressTaskId: null,
          vehicleId: null,
        });
      }
    }, []);

    return (
      <button
        data-testid="rapid-select-resource-btn"
        onClick={() => {
          // Rapidly select multiple resources
          selectItem(SelectedItemType.Driver, 1);
          selectItem(SelectedItemType.Driver, 2);
          selectItem(SelectedItemType.Driver, 3);
          selectItem(SelectedItemType.Driver, 4);
          selectItem(SelectedItemType.Driver, 5);
        }}
      >
        Rapid Select Resources
      </button>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestRapidResourceSelectComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  (setMapSourceMock as Mock).mockClear();
  const rapidSelectBtn = getByTestId('rapid-select-resource-btn');

  await act(async () => {
    rapidSelectBtn.click();
    // Wait for RAF to flush
    await new Promise((r) => setTimeout(r, 50));
  });

  // Should batch 5 rapid resource selections into 1-2 renders (not 5)
  const callCount = (setMapSourceMock as Mock).mock.calls.length;
  expect(callCount).toBeLessThan(5);
  expect(callCount).toBeGreaterThan(0);
});

test('flushMapUpdates applies updates with current selection state', async () => {
  const setMapSourceMock = await import('~/lib/map-helpers').then(
    (m) => m.setMapSource
  );
  (setMapSourceMock as Mock).mockClear();

  const TestFlushComponent = () => {
    const { selectItem, stationsRef } = useSimulation();

    useEffect(() => {
      stationsRef.current.set(1, {
        id: 1,
        name: 'Station 1',
        position: [0, 0],
        taskIds: [],
      });
      stationsRef.current.set(2, {
        id: 2,
        name: 'Station 2',
        position: [0, 0],
        taskIds: [],
      });
    }, []);

    return (
      <button
        data-testid="select-and-update"
        onClick={() => {
          selectItem(SelectedItemType.Station, 1);
          // Immediately select another - should batch and use final state
          selectItem(SelectedItemType.Station, 2);
        }}
      >
        Select and Update
      </button>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestFlushComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  (setMapSourceMock as Mock).mockClear();
  const selectBtn = getByTestId('select-and-update');

  await act(async () => {
    selectBtn.click();
    // Wait for RAF to flush
    await new Promise((r) => setTimeout(r, 50));
  });

  // Should have batched the two selections into fewer calls
  const callCount = (setMapSourceMock as Mock).mock.calls.length;
  // Without batching, we'd expect 4 calls (2 stations updates + 2 resources updates)
  // With batching, we expect 2 calls (1 stations update + 1 resources update)
  expect(callCount).toBeLessThanOrEqual(2);
  expect(callCount).toBeGreaterThan(0);

  // Verify the final station data has station 2 selected
  const stationCalls = (setMapSourceMock as Mock).mock.calls.filter(
    (call) => call[0] === 'stations'
  );
  expect(stationCalls.length).toBeGreaterThan(0);

  const lastStationCall = stationCalls[stationCalls.length - 1];
  const stationGeoJSON = lastStationCall[1];

  // Check that the GeoJSON has the correct selected station
  const selectedFeature = stationGeoJSON.features.find(
    (f: { properties: { selected: boolean } }) => f.properties.selected
  );
  expect(selectedFeature).toBeDefined();
  expect(selectedFeature.properties.id).toBe(2);
});

test('reorderTasks posts to API and updates resource task order', async () => {
  // Mock API to return successful response
  (api.post as Mock).mockResolvedValueOnce({
    data: { resource_id: 1, task_order: [20, 30, 10] },
  });

  const TestReorderComponent = () => {
    const { reorderTasks, driversRef, resourceBarElement } = useSimulation();

    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [10, 20, 30],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    const taskCount =
      resourceBarElement.find((r) => r.id === 1)?.taskCount || 0;

    return (
      <div>
        <div data-testid="task-count">{String(taskCount)}</div>
        <div data-testid="task-ids">
          {JSON.stringify(driversRef.current.get(1)?.taskIds || [])}
        </div>
        <button
          data-testid="reorder-btn"
          onClick={() => reorderTasks(1, [20, 30, 10], true)}
        >
          Reorder
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestReorderComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  expect(getByTestId('task-ids')).toHaveTextContent('[10,20,30]');

  const reorderBtn = getByTestId('reorder-btn');

  await act(async () => {
    reorderBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  expect(api.post).toHaveBeenCalledWith(
    '/simulation/test-sim-123/drivers/reorder-tasks',
    { driver_id: 1, task_ids: [20, 30, 10], apply_from_top: true }
  );

  await waitFor(() => {
    expect(getByTestId('task-ids')).toHaveTextContent('[20,30,10]');
    expect(getByTestId('task-count')).toHaveTextContent('3');
  });
});

test('reorderTasks handles API errors gracefully', async () => {
  const consoleErrorSpy = vi
    .spyOn(console, 'error')
    .mockImplementation(() => {});

  // Mock API to return error
  (api.post as Mock).mockRejectedValueOnce(new Error('Reorder failed'));

  const TestReorderErrorComponent = () => {
    const { reorderTasks, driversRef } = useSimulation();

    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [10, 20, 30],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    const handleReorder = async () => {
      try {
        await reorderTasks(1, [30, 20, 10], true);
      } catch {
        // Expected error - do nothing
      }
    };

    return (
      <div>
        <div data-testid="task-ids">
          {JSON.stringify(driversRef.current.get(1)?.taskIds || [])}
        </div>
        <button data-testid="reorder-btn" onClick={handleReorder}>
          Reorder
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestReorderErrorComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const reorderBtn = getByTestId('reorder-btn');

  await act(async () => {
    reorderBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  // Task order should remain unchanged after error
  await waitFor(() => {
    expect(getByTestId('task-ids')).toHaveTextContent('[10,20,30]');
  });

  consoleErrorSpy.mockRestore();
});

test('reorderTasks does nothing when resource does not exist', async () => {
  const consoleErrorSpy = vi
    .spyOn(console, 'error')
    .mockImplementation(() => {});

  const TestReorderNonexistentComponent = () => {
    const { reorderTasks } = useSimulation();

    const handleReorder = async () => {
      try {
        await reorderTasks(999, [10, 20, 30], true);
      } catch {
        // Expected error - do nothing
      }
    };

    return (
      <button data-testid="reorder-btn" onClick={handleReorder}>
        Reorder Nonexistent
      </button>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestReorderNonexistentComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  const reorderBtn = getByTestId('reorder-btn');

  await act(async () => {
    reorderBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  // API should not be called
  expect(api.post).not.toHaveBeenCalledWith(
    expect.stringContaining('reorder-tasks'),
    expect.anything()
  );

  consoleErrorSpy.mockRestore();
});

test('reorderTasks updates resourceBarElement and triggers map updates', async () => {
  // Mock API to return successful response
  (api.post as Mock).mockResolvedValueOnce({
    data: { resource_id: 1, task_order: [30, 10, 20] },
  });

  const setMapSourceMock = await import('~/lib/map-helpers').then(
    (m) => m.setMapSource
  );
  (setMapSourceMock as Mock).mockClear();

  const TestReorderMapUpdateComponent = () => {
    const { reorderTasks, driversRef, resourceBarElement } = useSimulation();

    useEffect(() => {
      driversRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskIds: [10, 20, 30],
        inProgressTaskId: null,
        vehicleId: null,
      });
    }, []);

    const taskCount =
      resourceBarElement.find((r) => r.id === 1)?.taskCount || 0;

    return (
      <div>
        <div data-testid="task-count">{String(taskCount)}</div>
        <button
          data-testid="reorder-btn"
          onClick={() => reorderTasks(1, [30, 10, 20], false)}
        >
          Reorder
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestReorderMapUpdateComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  (setMapSourceMock as Mock).mockClear();
  const reorderBtn = getByTestId('reorder-btn');

  await act(async () => {
    reorderBtn.click();
    await new Promise((r) => setTimeout(r, 50));
  });

  // Verify API was called with correct params
  expect(api.post).toHaveBeenCalledWith(
    '/simulation/test-sim-123/drivers/reorder-tasks',
    { driver_id: 1, task_ids: [30, 10, 20], apply_from_top: false }
  );

  // Verify map was updated (resources layer)
  await waitFor(() => {
    const resourcesCalls = (setMapSourceMock as Mock).mock.calls.filter(
      (call) => call[0] === 'resources'
    );
    expect(resourcesCalls.length).toBeGreaterThan(0);
  });

  // Verify task count remains the same
  expect(getByTestId('task-count')).toHaveTextContent('3');
});
