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
  type BackendPayload,
  type BackendStation,
  type BackendResource,
  type BackendTask,
  type StationTask,
} from '~/types';
import {
  adaptStationsToGeoJSON,
  adaptResourcesToGeoJSON,
} from '~/lib/geojson-adapters';
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
} from '~/lib/map-interactions';
import useError from '~/hooks/use-error';
import useAuth from '~/hooks/use-auth';
import {
  logMissingEntityError,
  logFrameProcessingError,
  logSimulationError,
} from '~/utils/simulation-error-utils';
import api from '~/api';

// Expect to receive frames every 1 second
const BASE_FRAME_INTERVAL_MS = 1000;

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

export const SPEED_OPTIONS = [0, 0.5, 1, 2, 4, 8] as const;
export type Speed = (typeof SPEED_OPTIONS)[number];

type SimulationContextType = {
  speedRef: React.RefObject<Speed>;
  stationsRef: React.RefObject<Map<number, Station>>;
  resourcesRef: React.RefObject<Map<number, Resource>>;
  resources: Resource[];
  tasks: StationTask[];
  selectedItem: SelectedItem | null;
  selectItem: (type: SelectedItemType, id: number) => void;
  clearSelection: () => void;
  assignTask: (resourceId: number, taskId: number) => Promise<void>;
  unassignTask: (resourceId: number, taskId: number) => Promise<void>;
  reassignTask: (
    prevResourceId: number,
    newResourceId: number,
    taskId: number
  ) => Promise<void>;
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
  const speedRef = useRef<Speed>(1);

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

  // Flag to trigger map render on next animation frame
  const renderOnNextFrameRef = useRef<boolean>(false);

  // (TOTAL) NON-REACTIVE SIMULATION ENTITY STATE
  const stationsRef = useRef<Map<number, Station>>(new Map());
  const resourcesRef = useRef<Map<number, Resource>>(new Map());
  const tasksRef = useRef<Map<number, StationTask>>(new Map());

  // (PARTIAL) REACTIVE SIMULATION ENTITY STATE
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);
  const [tasks, setTasks] = useState<StationTask[]>([]);

  const assignTask = async (resourceId: number, taskId: number) => {
    const resource = resourcesRef.current.get(resourceId);

    if (!resource) {
      throw new Error(`Resource #${resourceId} not found.`);
    }

    try {
      const payload = { task_id: taskId, resource_id: resourceId };
      await api.post(`/simulation/${simId!}/resources/assign`, payload);

      const updatedResource = {
        ...resource,
        taskList: [...(resource.taskList ?? [])],
      };

      if (!updatedResource.taskList.includes(taskId)) {
        updatedResource.taskList.push(taskId);
      }

      resourcesRef.current.set(resourceId, updatedResource);
      setResources(Array.from(resourcesRef.current.values()));
      updateSelectedItem(resourceId, updatedResource);
    } catch (error) {
      displayError(
        'Assignment failed',
        'An error occurred while assigning a task to a resource. Please try again later.'
      );
      throw error;
    }
  };

  const unassignTask = async (resourceId: number, taskId: number) => {
    const resource = resourcesRef.current.get(resourceId);
    if (!resource) {
      throw new Error(`Resource #${resourceId} not found.`);
    }

    try {
      const payload = { task_id: taskId, resource_id: resourceId };
      await api.post(`/simulation/${simId!}/resources/unassign`, payload);

      if (Array.isArray(resource.taskList)) {
        const updatedResource = {
          ...resource,
          taskList: resource.taskList.filter((t) => t !== taskId),
        };
        resourcesRef.current.set(resourceId, updatedResource);
        setResources(Array.from(resourcesRef.current.values()));
        updateSelectedItem(resourceId, updatedResource);
      }
    } catch (error) {
      displayError(
        'Unassignment failed',
        'An error occurred while unassigning a task from a resource. Please try again later.'
      );
      throw error;
    }
  };

  const reassignTask = async (
    prevResourceId: number,
    newResourceId: number,
    taskId: number
  ) => {
    const prevResource = resourcesRef.current.get(prevResourceId);
    const newResource = resourcesRef.current.get(newResourceId);
    if (!prevResource) {
      throw new Error(`Previous resource #${prevResourceId} not found.`);
    }
    if (!newResource) {
      throw new Error(`New resource #${newResourceId} not found.`);
    }

    try {
      const payload = {
        task_id: taskId,
        old_resource_id: prevResourceId,
        new_resource_id: newResourceId,
      };

      await api.post(`/simulation/${simId!}/resources/reassign`, payload);

      if (Array.isArray(prevResource.taskList)) {
        const updatedPrevResource = {
          ...prevResource,
          taskList: prevResource.taskList.filter((t) => t !== taskId),
        };
        resourcesRef.current.set(prevResourceId, updatedPrevResource);
      }

      const updatedNewResource = {
        ...newResource,
        taskList: Array.isArray(newResource.taskList)
          ? [...newResource.taskList]
          : [],
      };

      if (!updatedNewResource.taskList.includes(taskId)) {
        updatedNewResource.taskList.push(taskId);
      }

      resourcesRef.current.set(newResourceId, updatedNewResource);
      setResources(Array.from(resourcesRef.current.values()));
      if (selectedItem?.type === SelectedItemType.Resource) {
        if ((selectedItem.value as Resource).id === prevResourceId) {
          const updated = resourcesRef.current.get(prevResourceId);
          if (updated) {
            updateSelectedItem(prevResourceId, updated);
          }
        } else if ((selectedItem.value as Resource).id === newResourceId) {
          updateSelectedItem(newResourceId, updatedNewResource);
        }
      }
    } catch (error) {
      displayError(
        'Reassign failed',
        `An error occurred while reassigning task ${taskId} from resource ${prevResourceId} to resource ${newResourceId}. Please try again later.`
      );
      throw error;
    }
  };

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

  // Convert WebSocket simulation data to frontend format
  const adaptSimulationData = (
    payload: BackendPayload,
    isInitialFrame: boolean = false
  ) => {
    console.log(isInitialFrame);

    if (payload.tasks && payload.tasks.length > 0) {
      payload.tasks.forEach((task) =>
        tasksRef.current.set(task.id, {
          id: task.id,
          stationId: task.station_id,
          type: 'battery_swap',
          state: task.state === 'scheduled' ? 'open' : task.state,
          assigned_resource_id: task.assigned_resource_id,
        })
      );
      setTasks(Array.from(tasksRef.current.values()));
    }

    // Update stations that appear in the payload
    if (payload.stations && payload.stations.length > 0) {
      payload.stations.forEach((payloadStation: BackendStation) => {
        const position: [number, number] = payloadStation.station_position;
        const updatedStation: Station = {
          id: payloadStation.station_id,
          name: payloadStation.station_name,
          position: position,
          tasks: payloadStation.station_tasks.map((task: BackendTask) => ({
            id: task.id,
            stationId: task.station_id,
            type: 'battery_swap',
            state: task.state === 'scheduled' ? 'open' : task.state,
            assigned_resource_id: task.assigned_resource_id,
          })),
          task_count: payloadStation.task_count,
        };
        console.log('Updating station #', updatedStation);
        stationsRef.current.set(updatedStation.id, updatedStation);
        renderOnNextFrameRef.current = true;
      });
    }

    // Update resources that appear in the payload
    if (payload.resources && payload.resources.length > 0) {
      payload.resources.forEach((payloadResource: BackendResource) => {
        // Backend sends [lon, lat] which is what GeoJSON expects
        const position: [number, number] = payloadResource.resource_position;

        const adaptedResource: Resource = {
          id: payloadResource.resource_id,
          position: position,
          taskList: payloadResource.resource_tasks.map(
            (t: BackendTask) => t.id
          ),
          task_count: payloadResource.task_count,
          in_progress_task_id: payloadResource.in_progress_task_id,
        };
        resourcesRef.current.set(adaptedResource.id, adaptedResource);
        renderOnNextFrameRef.current = true;
      });
    }

    // Return all resources for state update
    return Array.from(resourcesRef.current.values());
  };

  // Helper function to update both map sources
  // TODO: Queue updates and batch them to next animation frame for better performance
  // Currently each call triggers immediate map re-render. Could maintain consistent RPS
  // by queueing updates and applying them only during the animation loop.
  // This would prevent extra renders when user rapidly selects/deselects entities.
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
      map.once('styledata', () => {
        updateMapSources(selectedStationId, selectedResourceId);
      });
      return;
    }

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

  const updateSelectedItem = (
    resourceId: number,
    updatedResource: Resource
  ) => {
    if (
      selectedItem?.type === SelectedItemType.Resource &&
      (selectedItem.value as Resource).id === resourceId
    ) {
      setSelectedItem({
        type: SelectedItemType.Resource,
        value: updatedResource,
      });
      selectedResourceIdRef.current = resourceId;
      updateMapSources(
        selectedStationIdRef.current,
        selectedResourceIdRef.current
      );
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

    try {
      // Store initial data (pass true to indicate this is initial frame)
      const updatedResources = adaptSimulationData(payload, true);
      setResources(updatedResources);

      // Initialize positions for all resources
      if (payload.resources) {
        payload.resources.forEach((resource: BackendResource) => {
          // Backend sends [lon, lat] which is what GeoJSON expects
          const position: [number, number] = resource.resource_position;
          frameStartPositionsRef.current.set(resource.resource_id, position);
          currentPositionsRef.current.set(resource.resource_id, position);
          targetPositionsRef.current.set(resource.resource_id, position);
        });
      }

      // Update initial frame time
      lastFrameTimeRef.current = performance.now();

      // Start animation loop
      ensureAnimationRunning();

      // Update map with initial data
      updateMapSources(
        selectedStationIdRef.current,
        selectedResourceIdRef.current
      );

      // Transition from loading to ready
      setSimulationStatus('ready');
    } catch (error) {
      logSimulationError(error, 'Failed to process initial frame', {
        errorType: 'INITIAL_FRAME_ERROR',
        payloadKeys: Object.keys(payload),
      });
      displayError(
        'Initialization Error',
        'Failed to initialize simulation. Please refresh and try again.'
      );
      setSimulationStatus('error');
    }
  };

  // Handle frame updates from WebSocket
  const handleFrameUpdate = (payload: BackendPayload) => {
    console.log('[WS] Handling frame update:', payload);

    try {
      // Update data (pass false to preserve existing tasks if not in payload)
      const updatedResources = adaptSimulationData(payload, false);
      setResources(updatedResources);

      // Update frame start time and positions for new frame
      const now = performance.now();
      lastFrameTimeRef.current = now;

      // For each resource, update the frame start position and target
      if (payload.resources) {
        payload.resources.forEach((resource: BackendResource) => {
          // Backend sends [lon, lat] which is what GeoJSON expects
          const newPosition: [number, number] = resource.resource_position;

          // Set frame start to current animated position
          const currentPos = currentPositionsRef.current.get(
            resource.resource_id
          );
          if (currentPos) {
            frameStartPositionsRef.current.set(
              resource.resource_id,
              currentPos
            );
          } else {
            frameStartPositionsRef.current.set(
              resource.resource_id,
              newPosition
            );
          }

          // Set new target
          targetPositionsRef.current.set(resource.resource_id, newPosition);
        });
      }

      // Ensure we're in running state
      if (simulationStatus !== 'running') {
        setSimulationStatus('running');
      }

      // Ensure animation loop is running (in case it stopped)
      ensureAnimationRunning();
    } catch (error) {
      logSimulationError(error, 'Failed to process frame update', {
        errorType: 'FRAME_UPDATE_ERROR',
        payloadKeys: Object.keys(payload),
      });
      // Don't show error dialog for individual frame failures - just log it
      // The simulation will continue with the last good state
    }
  };

  // Track if animation loop is running
  const isAnimatingRef = useRef<boolean>(false);

  // Start animation loop if not already running
  const ensureAnimationRunning = () => {
    if (!isAnimatingRef.current) {
      console.log('[Animation] Starting animation loop');
      isAnimatingRef.current = true;
      animationFrameRef.current = requestAnimationFrame(animateResources);
    }
  };

  // Animation loop to interpolate resource positions
  const animateResources = () => {
    const now = performance.now();
    const frameElapsedMs = now - lastFrameTimeRef.current;

    // Calculate interpolation progress (0 to 1)
    const adjustedInterval =
      speedRef.current === 0
        ? BASE_FRAME_INTERVAL_MS // If paused, use normal interval to avoid division by zero
        : BASE_FRAME_INTERVAL_MS / speedRef.current; // Adjust interval based on playback speed
    const t = Math.min(frameElapsedMs / adjustedInterval, 1);

    // Update position for each resource
    resourcesRef.current.forEach((resource) => {
      const start = frameStartPositionsRef.current.get(resource.id);
      const target = targetPositionsRef.current.get(resource.id);

      if (!start || !target) return;

      // Linear interpolation between start and target positions
      // TODO: Replace with route-based interpolation once backend sends GeoJSON routes
      // This will allow resources to follow actual roadways instead of straight lines
      const currentPos: [number, number] = [
        start[0] + (target[0] - start[0]) * t, // longitude
        start[1] + (target[1] - start[1]) * t, // latitude
      ];

      // Update current position
      const prevPos = currentPositionsRef.current.get(resource.id);
      if (
        !prevPos ||
        prevPos[0] !== currentPos[0] ||
        prevPos[1] !== currentPos[1]
      ) {
        currentPositionsRef.current.set(resource.id, currentPos);
        renderOnNextFrameRef.current = true;
      }

      // Update the resource object's position
      resource.position = currentPos;
    });

    // Only update map if positions or station tasks changed
    if (renderOnNextFrameRef.current) {
      updateMapSources(
        selectedStationIdRef.current,
        selectedResourceIdRef.current
      );
      renderOnNextFrameRef.current = false;
    }

    // Continue animation loop
    animationFrameRef.current = requestAnimationFrame(animateResources);
  };

  // ============================================================================
  // WEBSOCKET CONNECTION EFFECT
  // TODO: Extract WebSocket logic into useWebSocket hook for better maintainability
  // This effect is large and could be split into:
  // - useWebSocket (connection, message handling, reconnection)
  // - useSimulationAnimation (RAF loop, position interpolation)
  // - useSimulationData (data adapters, state management)
  // See: [Link to ticket/issue if you create one]
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

        // Handle initial frame (seq === 0)
        if (message.seq === 0) {
          console.log('[WS] 🎬 Initial frame received');
          handleInitialFrame(payload);
          return;
        }

        // Handle regular frames (seq > 0)
        if (message.seq > 0) {
          console.log('[WS] 🎞️  Frame', message.seq);
          handleFrameUpdate(payload);
          return;
        }

        console.warn('[WS] ⚠️  Unknown message:', message);
      } catch (error) {
        console.error('[WS] ❌ Parse error:', error);
        console.error('[WS] Raw data:', event.data);
        logFrameProcessingError(error, event.data?.seq || -1);
        displayError(
          'Simulation Frame Error',
          'An error occurred while processing simulation data. The simulation may not display correctly.'
        );
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] ❌ WebSocket error:', error);

      // Log to backend - WebSocket errors are client-side only
      logSimulationError(error, 'WebSocket connection error', {
        errorType: 'WEBSOCKET_ERROR',
        simId,
        wsUrl,
      });

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

      // Pause the simulation by setting playback speed to 0
      api
        .post(`/simulation/${simId!}/playbackSpeed`, { playback_speed: 0 })
        .then(() => {
          console.log('[WS] ⏸️  Playback paused on disconnect');
        })
        .catch((error) => {
          console.error('[WS] Failed to pause playback:', error);
        });

      // Code 1008 = Policy Violation (auth failure)
      if (event.code === 1008) {
        console.error('[WS] ❌ Authentication failed (code 1008)');

        // Log to backend - WebSocket close events are client-side only
        logSimulationError(
          new Error('WebSocket authentication failed'),
          'WebSocket closed due to authentication failure',
          {
            errorType: 'WEBSOCKET_AUTH_FAILURE',
            simId,
            closeCode: event.code,
            closeReason: event.reason,
          }
        );

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

    // Cleanup on unmount - defined here to avoid stale closures
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        isAnimatingRef.current = false;
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (hoverDebounceTimeoutRef.current) {
        clearTimeout(hoverDebounceTimeoutRef.current);
      }
    };
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
        speedRef,
        stationsRef,
        resourcesRef,
        resources,
        tasks: tasks,
        selectedItem,
        selectItem,
        clearSelection,
        assignTask,
        unassignTask,
        reassignTask,
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
