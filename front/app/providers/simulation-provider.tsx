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

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { useMap } from './map-provider';
import { MapSource, setMapSource } from '~/lib/map-helpers';
import {
  type Station,
  type Resource,
  type SelectedItem,
  SelectedItemType,
} from '~/types';
import {
  adaptStationsToGeoJSON,
  adaptResourcesToGeoJSON,
} from '~/lib/geojson-adapters';
import { interpolateAlongRoute } from '~/lib/animation-helpers';
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
} from '~/lib/map-interactions';
import useError from '~/hooks/use-error';
import useAuth from '~/hooks/use-auth';
import { logMissingEntityError } from '~/utils/simulation-error-utils';

// Expect to receive frames every 1 second
const FRAME_INTERVAL_MS = 1000;

// WebSocket reconnection settings
const MAX_RETRIES = 5;
const INITIAL_DELAY = 1000; // 1 second

type SimulationStatus =
  | 'idle' // Not connected
  | 'connecting' // WebSocket connecting
  | 'loading' // Connected, waiting for initial frame
  | 'ready' // Initial frame received, can interact
  | 'running' // Frames streaming
  | 'error'; // Error state

type SimulationContextType = {
  stationsRef: React.RefObject<Map<number, Station>>;
  resourcesRef: React.RefObject<Map<number, Resource>>;
  resources: Resource[];
  selectedItem: SelectedItem | null;
  selectItem: (type: SelectedItemType, id: number) => void;
  clearSelection: () => void;
  assignTaskToResource: (resourceId: number, taskId: number) => void;
  simId: string | null;
  isConnected: boolean;
  simulationStatus: SimulationStatus;
  isLoading: boolean; // Convenience flag for UI
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

interface SimulationProviderProps {
  children: ReactNode;
  simId?: string;
}

export const SimulationProvider = ({
  children,
  simId: initialSimId,
}: SimulationProviderProps) => {
  const { displayError } = useError();
  const { user } = useAuth();
  const { mapRef, mapLoaded } = useMap();
  const stationsRef = useRef<Map<number, Station>>(new Map());
  const resourcesRef = useRef<Map<number, Resource>>(new Map());

  // Simulation state
  const [simId] = useState<string | null>(initialSimId || null);
  const [isConnected, setIsConnected] = useState(false);
  const [simulationStatus, setSimulationStatus] =
    useState<SimulationStatus>('idle');
  const [connectionAttempts, setConnectionAttempts] = useState(0);

  // Derived loading state for convenience
  const isLoading =
    simulationStatus === 'connecting' || simulationStatus === 'loading';

  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);

  // Resources state for components that need to react to changes
  const [resources, setResources] = useState<Resource[]>([]);

  // Selection state
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);

  // Hover state - use refs so animation loop always has latest values
  const hoveredStationIdRef = useRef<number | null>(null);
  const hoveredResourceIdRef = useRef<number | null>(null);

  // Debounce hover updates to prevent excessive re-renders
  const hoverDebounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Ref to track selected IDs for animation loop
  const selectedStationIdRef = useRef<number | undefined>(undefined);
  const selectedResourceIdRef = useRef<number | undefined>(undefined);

  // Position tracking for each resource
  const frameStartPositionsRef = useRef<Map<number, [number, number]>>(
    new Map()
  );
  const currentPositionsRef = useRef<Map<number, [number, number]>>(new Map());
  const targetPositionsRef = useRef<Map<number, [number, number]>>(new Map());

  // Global frame timing (shared by all resources)
  const lastFrameTimeRef = useRef<number>(0);

  // Animation and cleanup refs
  const animationFrameRef = useRef<number>(0);

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  // Backend WebSocket payload types (snake_case from backend)
  interface BackendTask {
    id: number;
    station_id: number;
    state: 'open' | 'assigned' | 'inprogress' | 'completed';
    assigned_resource_id: number | null;
  }

  interface BackendStation {
    station_id: number;
    station_name: string;
    station_position: [number, number];
    station_tasks: BackendTask[];
    task_count: number;
  }

  interface BackendResource {
    resource_id: number;
    resource_position: [number, number];
    resource_tasks: BackendTask[];
    task_count: number;
    in_progress_task_id: number | null;
  }

  interface BackendPayload {
    stations?: BackendStation[];
    resources?: BackendResource[];
  }

  // Convert WebSocket simulation data to frontend format
  const adaptSimulationData = (payload: BackendPayload) => {
    // Merge stations (don't clear, just update what's in the payload)
    if (payload.stations) {
      payload.stations.forEach((station: BackendStation) => {
        const adaptedStation: Station = {
          id: station.station_id,
          name: station.station_name,
          position: station.station_position,
          tasks: station.station_tasks.map((task: BackendTask) => ({
            id: task.id,
            stationId: task.station_id,
            type: 'battery_swap',
            state: task.state,
            assigned_resource_id: task.assigned_resource_id,
          })),
          task_count: station.task_count,
        };
        stationsRef.current.set(adaptedStation.id, adaptedStation);
      });
    }

    // Merge resources (don't clear, just update what's in the payload)
    if (payload.resources) {
      payload.resources.forEach((resource: BackendResource) => {
        const adaptedResource: Resource = {
          id: resource.resource_id,
          position: resource.resource_position,
          taskList: resource.resource_tasks.map((t: BackendTask) => t.id),
          task_count: resource.task_count,
          in_progress_task_id: resource.in_progress_task_id,
        };
        resourcesRef.current.set(adaptedResource.id, adaptedResource);
      });
    }

    // Return all resources for state update
    return Array.from(resourcesRef.current.values());
  };

  // Helper function to update both map sources
  const updateMapSources = (
    selectedStationId?: number,
    selectedResourceId?: number
  ) => {
    if (!mapRef.current) {
      console.log('[Map] mapRef is null');
      return;
    }

    const map = mapRef.current;

    // Check if map style is loaded
    if (!map.isStyleLoaded()) {
      console.log('[Map] Style not loaded yet, waiting...');
      map.once('styledata', () => {
        console.log('[Map] Style loaded, retrying update');
        updateMapSources(selectedStationId, selectedResourceId);
      });
      return;
    }

    console.log('[Map] Updating sources');

    // Update stations
    if (stationsRef.current.size > 0) {
      const stations = Array.from(stationsRef.current.values());
      const geojson = adaptStationsToGeoJSON(
        stations,
        selectedStationId,
        hoveredStationIdRef.current ?? undefined
      );
      setMapSource(MapSource.Stations, geojson, map);
    }

    // Update resources
    if (resourcesRef.current.size > 0) {
      const resources = Array.from(resourcesRef.current.values());
      const geojson = adaptResourcesToGeoJSON(
        resources,
        selectedResourceId,
        hoveredResourceIdRef.current ?? undefined
      );
      setMapSource(MapSource.Resources, geojson, map);
    }
  };

  // Clear selection function
  const clearSelection = () => {
    if (!mapLoaded) return;

    setSelectedItem(null);
    selectedStationIdRef.current = undefined;
    selectedResourceIdRef.current = undefined;

    updateMapSources(undefined, undefined);
  };

  // Selection function
  const selectItem = (type: SelectedItemType, id: number) => {
    if (!mapLoaded) return;

    // Get the item and validate it exists
    const item =
      type === SelectedItemType.Station
        ? stationsRef.current.get(id)
        : resourcesRef.current.get(id);

    if (!item) {
      const entityType =
        type === SelectedItemType.Station ? 'station' : 'resource';
      logMissingEntityError(entityType, id);

      const capitalizedType =
        entityType.charAt(0).toUpperCase() + entityType.slice(1);
      displayError(
        `${capitalizedType} not found`,
        `Failed to load ${entityType} details. Please try again later.`
      );
      return;
    }

    setSelectedItem({ type, value: item });

    if (type === SelectedItemType.Station) {
      selectedStationIdRef.current = id;
      selectedResourceIdRef.current = undefined;
    } else {
      selectedResourceIdRef.current = id;
      selectedStationIdRef.current = undefined;
    }

    updateMapSources(
      type === SelectedItemType.Station ? id : undefined,
      type === SelectedItemType.Resource ? id : undefined
    );
  };

  // Update hover state with immediate visual feedback
  const updateHoverState = (
    stationId: number | null,
    resourceId: number | null
  ) => {
    hoveredStationIdRef.current = stationId;
    hoveredResourceIdRef.current = resourceId;

    if (hoverDebounceTimeoutRef.current) {
      clearTimeout(hoverDebounceTimeoutRef.current);
    }

    hoverDebounceTimeoutRef.current = setTimeout(() => {
      updateMapSources(
        selectedStationIdRef.current,
        selectedResourceIdRef.current
      );
    }, 16); // ~60fps
  };

  // Handle initial frame from WebSocket
  const handleInitialFrame = (payload: BackendPayload) => {
    console.log('[WS] Handling initial frame:', payload);

    // Store initial data
    const updatedResources = adaptSimulationData(payload);
    setResources(updatedResources);

    // Initialize positions for all resources
    if (payload.resources) {
      payload.resources.forEach((resource: BackendResource) => {
        const position: [number, number] = resource.resource_position;
        frameStartPositionsRef.current.set(resource.resource_id, position);
        currentPositionsRef.current.set(resource.resource_id, position);
        targetPositionsRef.current.set(resource.resource_id, position);
      });
    }

    // Update initial frame time
    lastFrameTimeRef.current = performance.now();

    // Start animation loop
    console.log('[Animation] Starting animation loop');
    animationFrameRef.current = requestAnimationFrame(animateResources);

    // Update map with initial data
    updateMapSources(
      selectedStationIdRef.current,
      selectedResourceIdRef.current
    );

    // Transition from loading to ready
    setSimulationStatus('ready');
  };

  // Handle frame updates from WebSocket
  const handleFrameUpdate = (payload: BackendPayload) => {
    console.log('[WS] Handling frame update:', payload);

    // Update data
    const updatedResources = adaptSimulationData(payload);
    setResources(updatedResources);

    // Update frame start time and positions for new frame
    const now = performance.now();
    lastFrameTimeRef.current = now;

    // For each resource, update the frame start position and target
    if (payload.resources) {
      payload.resources.forEach((resource: BackendResource) => {
        const newPosition: [number, number] = resource.resource_position;

        // Set frame start to current animated position
        const currentPos = currentPositionsRef.current.get(
          resource.resource_id
        );
        if (currentPos) {
          frameStartPositionsRef.current.set(resource.resource_id, currentPos);
        } else {
          frameStartPositionsRef.current.set(resource.resource_id, newPosition);
        }

        // Set new target
        targetPositionsRef.current.set(resource.resource_id, newPosition);
      });
    }

    // Ensure we're in running state
    if (simulationStatus !== 'running') {
      setSimulationStatus('running');
    }
  };

  // Animation loop to interpolate resource positions
  const animateResources = () => {
    const now = performance.now();
    const frameElapsedMs = now - lastFrameTimeRef.current;

    // Calculate interpolation progress (0 to 1)
    const t = Math.min(frameElapsedMs / FRAME_INTERVAL_MS, 1);

    let needsUpdate = false;

    // Update position for each resource
    resourcesRef.current.forEach((resource) => {
      const start = frameStartPositionsRef.current.get(resource.id);
      const target = targetPositionsRef.current.get(resource.id);

      if (!start || !target) return;

      // Interpolate position
      const routeGeometry = resource.route?.coordinates || [];
      const currentPos = interpolateAlongRoute(routeGeometry, start, target, t);

      // Update current position
      const prevPos = currentPositionsRef.current.get(resource.id);
      if (
        !prevPos ||
        prevPos[0] !== currentPos[0] ||
        prevPos[1] !== currentPos[1]
      ) {
        currentPositionsRef.current.set(resource.id, currentPos);
        needsUpdate = true;
      }

      // Update the resource object's position
      resource.position = currentPos;
    });

    // Only update map if positions changed
    if (needsUpdate) {
      updateMapSources(
        selectedStationIdRef.current,
        selectedResourceIdRef.current
      );
    }

    // Continue animation loop
    animationFrameRef.current = requestAnimationFrame(animateResources);
  };

  const assignTaskToResource = (resourceId: number, taskId: number) => {
    try {
      // TODO: use /assign endpoint
      console.log('assignTaskToResource', { resourceId, taskId });
    } catch (error) {
      console.error('Error assigning task to resource:', error);
    }
  };

  // Cleanup animation and WebSocket on unmount
  const cleanup = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (hoverDebounceTimeoutRef.current) {
      clearTimeout(hoverDebounceTimeoutRef.current);
    }
  };

  // ============================================================================
  // WEBSOCKET CONNECTION EFFECT
  // ============================================================================

  useEffect(() => {
    if (!mapLoaded || !simId || !user) {
      console.log('[WS] ⏳ Waiting for prerequisites...', {
        mapLoaded,
        simId: !!simId,
        hasUser: !!user,
      });
      return;
    }

    console.log('[WS] 🚀 Connecting to WebSocket...');

    // Build WebSocket URL
    const apiBaseUrl = import.meta.env.VITE_BACKEND_URL;
    const url = apiBaseUrl ? new URL(apiBaseUrl) : null;
    const wsProtocol =
      url?.protocol === 'https:' || window.location.protocol === 'https:'
        ? 'wss:'
        : 'ws:';
    const wsHost = url?.host || window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/simulation/stream/${simId}`;

    console.log('[WS] URL:', wsUrl);
    console.log('[WS] Cookie will be sent automatically by browser');

    setSimulationStatus('connecting');

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] ✅ Connection opened');
      setIsConnected(true);
      setConnectionAttempts(0);
      // Set to loading state - waiting for initial frame
      setSimulationStatus('loading');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        // Handle status messages
        if (message.type === 'status') {
          console.log('[WS] 📊 Status:', message.message, message);
          // Status messages are informational, don't change state
          return;
        }

        // Handle error messages
        if (message.type === 'error') {
          console.error('[WS] ❌ Server Error:', message.message);
          displayError(
            'Simulation Error',
            message.message || 'An error occurred'
          );
          setSimulationStatus('error');
          return;
        }

        // Parse payload if it's a string
        let payload = message.payload;
        if (typeof payload === 'string') {
          payload = JSON.parse(payload);
        }

        // Handle initial frame (seq_numb === 0)
        if (message.seq_numb === 0) {
          console.log('[WS] 🎬 Initial frame received');
          handleInitialFrame(payload);
          return;
        }

        // Handle regular frames (seq_numb > 0)
        if (message.seq_numb > 0) {
          console.log('[WS] 🎞️  Frame', message.seq_numb);
          handleFrameUpdate(payload);
          return;
        }

        console.warn('[WS] ⚠️  Unknown message:', message);
      } catch (error) {
        console.error('[WS] ❌ Parse error:', error);
        console.error('[WS] Raw data:', event.data);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] ❌ WebSocket error:', error);
      displayError(
        'Connection Error',
        'Failed to connect to simulation. Check authentication and try again.'
      );
      setSimulationStatus('error');
    };

    ws.onclose = (event) => {
      console.log('[WS] 🔌 Connection closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });

      setIsConnected(false);

      // Code 1008 = Policy Violation (auth failure)
      if (event.code === 1008) {
        console.error('[WS] ❌ Authentication failed (code 1008)');
        displayError(
          'Authentication Failed',
          'WebSocket authentication failed. Please try logging in again.'
        );
        setSimulationStatus('error');
        return;
      }

      if (simulationStatus !== 'error') {
        setSimulationStatus('idle');
      }

      // Retry logic for network errors
      if (connectionAttempts < MAX_RETRIES && event.code === 1006) {
        const delay = INITIAL_DELAY * Math.pow(2, connectionAttempts);
        console.log(
          `[WS] 🔄 Retry ${connectionAttempts + 1}/${MAX_RETRIES} in ${delay}ms`
        );

        setTimeout(() => {
          setConnectionAttempts((prev) => prev + 1);
        }, delay);
      }
    };

    // Set up map interactions
    if (mapRef.current) {
      setupMapClickHandlers(mapRef.current, (item) => {
        if (!item) {
          clearSelection();
          return;
        }
        const { type, id } = item;
        selectItem(type, id);
      });

      setupMapHoverHandlers(mapRef.current, (item) => {
        if (!item) {
          updateHoverState(null, null);
          return;
        }
        const { type, id } = item;
        if (type === SelectedItemType.Station) {
          updateHoverState(id, null);
        } else if (type === SelectedItemType.Resource) {
          updateHoverState(null, id);
        }
      });
    }

    // Cleanup on unmount
    return cleanup;
  }, [mapLoaded, simId, user, connectionAttempts]);

  // Render existing data when map loads
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;

    if (stationsRef.current.size > 0 || resourcesRef.current.size > 0) {
      console.log('[Map] Map loaded, rendering existing data');
      updateMapSources(
        selectedStationIdRef.current,
        selectedResourceIdRef.current
      );
    }
  }, [mapLoaded]);

  // ============================================================================
  // CONTEXT PROVIDER
  // ============================================================================

  return (
    <SimulationContext.Provider
      value={{
        stationsRef,
        resourcesRef,
        resources,
        selectedItem,
        selectItem,
        clearSelection,
        assignTaskToResource,
        simId,
        isConnected,
        simulationStatus,
        isLoading,
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = (): SimulationContextType => {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
};
