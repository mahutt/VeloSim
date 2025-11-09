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

// Mock WebSocket
interface MockWebSocket {
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  send: (data: string) => void;
  close: () => void;
}

let mockWebSocketInstance: MockWebSocket | null = null;

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

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  constructor(_url: string) {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    mockWebSocketInstance = this;
  }
}

// Helper to get the current WebSocket mock instance
function getMockedWebSocket(): MockWebSocket {
  if (!mockWebSocketInstance) {
    throw new Error('WebSocket mock instance not available');
  }
  return mockWebSocketInstance;
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
import { MockMap, mockDisplayError } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';
import { SelectedItemType } from '~/types';
import {
  logSimulationError,
  logMissingEntityError,
} from '~/utils/simulation-error-utils';

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
  mockWebSocketInstance = null; // Reset WebSocket instance
  rafCallCount = 0; // Reset RAF call count

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
        tasks: [],
        task_count: 0,
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
    const { selectItem, selectedItem, resourcesRef } = useSimulation();

    // Manually add a resource to test selection
    useEffect(() => {
      resourcesRef.current.set(1, {
        id: 1,
        position: [0, 0],
        taskList: [],
        task_count: 0,
        in_progress_task_id: null,
      });
    }, []);

    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? `resource-${selectedItem.value.id}` : 'none'}
        </div>
        <button
          data-testid="select-btn"
          onClick={() => selectItem(SelectedItemType.Resource, 1)}
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

test('assignTaskToResource logs the assignment', () => {
  const consoleLogSpy = vi.spyOn(console, 'log');

  const TestComponentWithAssign = () => {
    const { assignTaskToResource } = useSimulation();

    return (
      <button
        data-testid="assign-btn"
        onClick={() => assignTaskToResource(1, 2)}
      >
        Assign
      </button>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponentWithAssign />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  const assignBtn = getByTestId('assign-btn');

  act(() => {
    assignBtn.click();
  });

  expect(consoleLogSpy).toHaveBeenCalledWith('assignTaskToResource', {
    resourceId: 1,
    taskId: 2,
  });

  consoleLogSpy.mockRestore();
});

test('WebSocket connects when all prerequisites are met', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  // Wait for map to be created and trigger load event
  await waitFor(() => {
    expect(MockMap.instance).toBeDefined();
  });

  await act(async () => {
    MockMap.instance?.callBacks['load']();
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('connecting');
  });

  // Verify WebSocket was created
  const mockWs = getMockedWebSocket();
  expect(mockWs).toBeDefined();
  expect(mockWs.onopen).toBeDefined();
});

test('WebSocket handles initial frame (seq_numb === 0)', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  // Wait for WebSocket connection
  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('connecting');
  });

  const mockWs = getMockedWebSocket();

  // Simulate WebSocket open
  await act(async () => {
    mockWs.onopen?.(new Event('open'));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('loading');
    expect(getByTestId('connected')).toHaveTextContent('true');
  });

  // Send initial frame
  const initialFrame = {
    type: 'frame',
    seq: 0,
    payload: {
      resources: [
        {
          resource_id: 1,
          resource_position: [45.5, -73.6],
          resource_tasks: [],
          task_count: 0,
          in_progress_task_id: null,
        },
      ],
      stations: [
        {
          station_id: 1,
          station_name: 'Station A',
          station_position: [45.5, -73.6],
          station_tasks: [],
          task_count: 0,
        },
      ],
    },
  };

  await act(async () => {
    mockWs.onmessage?.(
      new MessageEvent('message', { data: JSON.stringify(initialFrame) })
    );
    // Allow state updates and effects to complete
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('ready');
  });
});

test('WebSocket handles frame updates (seq_numb > 0)', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('connecting');
  });

  const mockWs = getMockedWebSocket();

  await act(async () => {
    mockWs.onopen?.(new Event('open'));
  });

  // Send initial frame first
  const initialFrame = {
    type: 'frame',
    seq: 0,
    payload: {
      resources: [
        {
          resource_id: 1,
          resource_position: [45.5, -73.6],
          resource_tasks: [],
          task_count: 0,
          in_progress_task_id: null,
        },
      ],
      stations: [],
    },
  };

  await act(async () => {
    mockWs.onmessage?.(
      new MessageEvent('message', { data: JSON.stringify(initialFrame) })
    );
    // Allow state updates and effects to complete
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('ready');
  });

  // Send frame update
  const frameUpdate = {
    type: 'frame',
    seq: 1,
    payload: {
      resources: [
        {
          resource_id: 1,
          resource_position: [45.51, -73.61],
          resource_tasks: [],
          task_count: 0,
          in_progress_task_id: null,
        },
      ],
      stations: [],
    },
  };

  await act(async () => {
    mockWs.onmessage?.(
      new MessageEvent('message', { data: JSON.stringify(frameUpdate) })
    );
    // Allow state updates and effects to complete
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('running');
  });
});

test('WebSocket handles status messages', async () => {
  const consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

  render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  const mockWs = getMockedWebSocket();

  await act(async () => {
    mockWs.onopen?.(new Event('open'));
  });

  // Send status message
  const statusMessage = {
    type: 'status',
    message: 'Simulation started',
  };

  await act(async () => {
    mockWs.onmessage?.(
      new MessageEvent('message', { data: JSON.stringify(statusMessage) })
    );
  });

  // Status messages don't change state, just log
  expect(consoleLogSpy).toHaveBeenCalledWith(
    '[WS] 📊 Status:',
    'Simulation started',
    statusMessage
  );

  consoleLogSpy.mockRestore();
});

test('WebSocket handles error messages', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  const mockWs = getMockedWebSocket();

  await act(async () => {
    mockWs.onopen?.(new Event('open'));
  });

  // Send error message
  const errorMessage = {
    type: 'error',
    message: 'Simulation failed',
  };

  await act(async () => {
    mockWs.onmessage?.(
      new MessageEvent('message', { data: JSON.stringify(errorMessage) })
    );
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('error');
  });

  expect(mockDisplayError).toHaveBeenCalledWith(
    'Simulation Error',
    'Simulation failed'
  );
});

test('WebSocket handles connection errors', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  const mockWs = getMockedWebSocket();

  // Simulate WebSocket error
  await act(async () => {
    mockWs.onerror?.(new Event('error'));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('error');
  });

  expect(mockDisplayError).toHaveBeenCalledWith(
    'Connection Error',
    'Failed to connect to simulation. Check authentication and try again.'
  );
});

test('WebSocket handles authentication failure (code 1008)', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  const mockWs = getMockedWebSocket();

  await act(async () => {
    mockWs.onopen?.(new Event('open'));
  });

  // Wait for status to update to 'loading'
  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('loading');
  });

  // Simulate close with auth failure
  await act(async () => {
    // Create a manual close event object since CloseEvent constructor doesn't work properly in tests
    const closeEvent = {
      type: 'close',
      code: 1008,
      reason: 'Policy Violation',
      wasClean: false,
    } as CloseEvent;
    mockWs.onclose?.(closeEvent);
    // Allow state updates to complete
    await new Promise((resolve) => setTimeout(resolve, 50));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('error');
    expect(getByTestId('connected')).toHaveTextContent('false');
  });

  expect(mockDisplayError).toHaveBeenCalledWith(
    'Authentication Failed',
    'WebSocket authentication failed. Please try logging in again.'
  );
});

test('WebSocket handles normal close', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider simId="test-sim-123">
        <TaskAssignmentProvider>
          <MapContainer />
          <TestComponent />
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

  const mockWs = getMockedWebSocket();

  await act(async () => {
    mockWs.onopen?.(new Event('open'));
  });

  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('loading');
  });

  // Simulate normal close
  await act(async () => {
    const closeEvent = {
      type: 'close',
      code: 1000,
      reason: 'Normal closure',
      wasClean: true,
    } as CloseEvent;
    mockWs.onclose?.(closeEvent);
  });

  await waitFor(() => {
    expect(getByTestId('connected')).toHaveTextContent('false');
    expect(getByTestId('status')).toHaveTextContent('idle');
  });
});
