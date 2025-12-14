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
  useCallback,
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
  type SimulationStatus,
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
import { logMissingEntityError } from '~/utils/simulation-error-utils';
import api from '~/api';
import { useSimulationWebSocket } from '~/hooks/use-simulation-websocket';
import {
  formatSecondsToHHMM,
  calculateDayFromSeconds,
} from '~/utils/clock-utils';

// Expect to receive frames every 1 second
const BASE_FRAME_INTERVAL_MS = 1000;

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
  formattedSimTime: string | null;
  currentDay: number;
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

  // Flag to trigger map render on next animation frame
  const renderOnNextFrameRef = useRef<boolean>(false);

  // RAF queue system for batched map updates
  const mapUpdatePendingRef = useRef<boolean>(false);
  const mapUpdateRafIdRef = useRef<number | null>(null);

  // (TOTAL) NON-REACTIVE SIMULATION ENTITY STATE
  const stationsRef = useRef<Map<number, Station>>(new Map());
  const resourcesRef = useRef<Map<number, Resource>>(new Map());
  const tasksRef = useRef<Map<number, StationTask>>(new Map());

  // (PARTIAL) REACTIVE SIMULATION ENTITY STATE
  const [resources, setResources] = useState<Resource[]>([]);
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);
  const [tasks, setTasks] = useState<StationTask[]>([]);

  const [formattedSimTime, setFormattedSimTime] = useState<string | null>(null);
  const [currentDay, setCurrentDay] = useState<number>(1);

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

    // Always update tasks (including closed ones)
    // Backend sends all tasks with their current status
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

  // Flush batched map updates using current selection state
  const flushMapUpdates = () => {
    mapUpdatePendingRef.current = false;
    mapUpdateRafIdRef.current = null;
    updateMapSources(
      selectedStationIdRef.current,
      selectedResourceIdRef.current
    );
  };

  // Queue a map update to be applied on next animation frame
  // This batches multiple updates together for consistent 60 RPS
  const queueMapUpdate = () => {
    mapUpdatePendingRef.current = true;

    // Only schedule RAF if not already scheduled
    if (mapUpdateRafIdRef.current === null) {
      mapUpdateRafIdRef.current = requestAnimationFrame(flushMapUpdates);
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
      queueMapUpdate();
    }
  };

  // Clear selection function
  const clearSelection = () => {
    if (!mapLoaded) return;

    setSelectedItem(null);
    selectedStationIdRef.current = undefined;
    selectedResourceIdRef.current = undefined;

    queueMapUpdate();
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

    queueMapUpdate();
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
      queueMapUpdate();
    }, 16); // ~60fps
  };

  // Handle initial frame from WebSocket
  const handleInitialFrame = useCallback((payload: BackendPayload) => {
    console.log('[WS] Handling initial frame:', payload);

    if (payload.clock) {
      setFormattedSimTime(
        formatSecondsToHHMM(
          payload.clock.simSecondsPassed,
          payload.clock.startTime
        )
      );
      setCurrentDay(
        calculateDayFromSeconds(
          payload.clock.simSecondsPassed,
          payload.clock.startTime
        )
      );
    }

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
    queueMapUpdate();
  }, []);

  // Handle frame updates from WebSocket
  const handleFrameUpdate = useCallback((payload: BackendPayload) => {
    console.log('[WS] Handling frame update:', payload);

    if (payload.clock) {
      setFormattedSimTime(
        formatSecondsToHHMM(
          payload.clock.simSecondsPassed,
          payload.clock.startTime
        )
      );
      setCurrentDay(
        calculateDayFromSeconds(
          payload.clock.simSecondsPassed,
          payload.clock.startTime
        )
      );
    }
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
          frameStartPositionsRef.current.set(resource.resource_id, currentPos);
        } else {
          frameStartPositionsRef.current.set(resource.resource_id, newPosition);
        }

        // Set new target
        targetPositionsRef.current.set(resource.resource_id, newPosition);
      });
    }

    // Ensure animation loop is running (in case it stopped)
    ensureAnimationRunning();
  }, []);

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
      // Call updateMapSources directly since we're already in a RAF callback
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
  // WEBSOCKET CONNECTION
  // WebSocket connection is managed by useSimulationWebSocket hook
  // ============================================================================

  const { isConnected, simulationStatus } = useSimulationWebSocket({
    simId,
    enabled: mapLoaded && !!user,
    onInitialFrame: handleInitialFrame,
    onFrameUpdate: handleFrameUpdate,
    onError: displayError,
  });

  // Derived loading state for convenience
  const isLoading =
    simulationStatus === 'connecting' || simulationStatus === 'loading';

  // ============================================================================
  // MAP INTERACTIONS SETUP
  // ============================================================================

  useEffect(() => {
    if (!mapLoaded) return;

    // Set up map interactions
    setupMapClickHandlers(mapRef.current!, (item) => {
      if (!item) {
        clearSelection();
        return;
      }
      const { type, id } = item;
      selectItem(type, id);
    });

    setupMapHoverHandlers(mapRef.current!, (item) => {
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
  }, [mapLoaded]);

  // ============================================================================
  // ANIMATION CLEANUP
  // ============================================================================

  useEffect(() => {
    // Cleanup animation loop on unmount
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        isAnimatingRef.current = false;
      }
      if (mapUpdateRafIdRef.current !== null) {
        cancelAnimationFrame(mapUpdateRafIdRef.current);
        mapUpdateRafIdRef.current = null;
      }
      if (hoverDebounceTimeoutRef.current) {
        clearTimeout(hoverDebounceTimeoutRef.current);
      }
    };
  }, []);

  // Render existing data when map loads
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;

    if (stationsRef.current.size > 0 || resourcesRef.current.size > 0) {
      console.log('[Map] Map loaded, rendering existing data');
      queueMapUpdate();
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
        formattedSimTime,
        currentDay,
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
