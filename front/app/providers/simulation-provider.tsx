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
import {
  MapSource,
  setMapSource,
  updateRouteDisplay,
  updateAllRoutesDisplay,
  clearAllRoutesDisplay,
} from '~/lib/map-helpers';
import {
  type BackendPayload,
  type StationTask,
  type Station,
  type Position,
  type Driver,
  type Route,
  type Headquarters,
  type Vehicle,
  SimulationMode,
} from '~/types';
import {
  adaptStationsToGeoJSON,
  adaptResourcesToGeoJSON,
  adaptHeadquartersToGeoJSON,
} from '~/lib/geojson-adapters';
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
} from '~/lib/map-interactions';
import useError from '~/hooks/use-error';
import { logMissingEntityError } from '~/utils/simulation-error-utils';
import api from '~/api';
import {
  formatSecondsToHHMM,
  calculateDayFromSeconds,
} from '~/utils/clock-utils';
import type { ResourceBarElement } from '~/components/resource/resource-bar';
import {
  SelectedItemType,
  type SelectedItemBarElement,
} from '~/components/map/selected-item-bar';
import { updateDriverPositions } from '~/lib/animation-helpers';
import type { HQWidgetProps } from '~/components/simulation/hq-widget';
import {
  areHQWidgetStatesEqual,
  createHQWidgetState,
} from '~/lib/hq-widget-helpers';
import { positionsEqual } from '~/lib/utils';
import {
  driverResourceHasUpdated,
  vehicleResourceHasUpdated,
} from '~/lib/simulation-helpers';
import { ServerFrameSource } from '~/lib/frame-sources/server-frame-source';
import { LocalFrameSource } from '~/lib/frame-sources/local-frame-source';

export const SPEED_OPTIONS = [0, 0.5, 1, 2, 4, 8] as const;
export type Speed = (typeof SPEED_OPTIONS)[number];
export type NonZeroSpeed = Exclude<Speed, 0>;

export type SimulationContextType = {
  speedRef: React.RefObject<Speed>;
  stationsRef: React.RefObject<Map<number, Station>>;
  driversRef: React.RefObject<Map<number, Driver>>;
  vehiclesRef: React.RefObject<Map<number, Vehicle>>;
  resourceBarElement: ResourceBarElement;
  selectedItem: SelectedItemBarElement | null;
  selectItem: (type: SelectedItemType, id: number) => void;
  clearSelection: () => void;
  assignTask: (driverId: number, taskId: number) => Promise<void>;
  unassignTask: (driverId: number, taskId: number) => Promise<void>;
  reassignTask: (
    prevDriverId: number,
    newDriverId: number,
    taskId: number
  ) => Promise<void>;
  reorderTasks: (
    driverId: number,
    taskIds: number[],
    applyFromTop: boolean
  ) => Promise<void>;
  simId: string | null;
  isLoading: boolean;
  formattedSimTime: string | null;
  currentDay: number;
  HQWidgetState: HQWidgetProps;
  showAllRoutes: boolean;
  toggleShowAllRoutes: () => void;
  speed: NonZeroSpeed;
  setSpeed: (speed: NonZeroSpeed) => Promise<void>;
  paused: boolean;
  setPaused: (paused: boolean) => Promise<void>;
  scrub: (seconds: number) => void;
  commitScrub: (seconds: number) => void;
  startTime: number;
  simulationSecondsPassed: number;
  scrubSimulationSecond: number;
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

interface SimulationProviderProps {
  children: ReactNode;
  simId: string;
}

export const SimulationProvider = ({
  children,
  simId: initialSimId,
}: SimulationProviderProps) => {
  const { displayError } = useError();
  const { mapRef, mapLoaded } = useMap();

  const [startTime, setStartTime] = useState<number>(0);
  const speedRef = useRef<Speed>(1);
  const [nonZeroSpeed, _setSpeed] = useState<NonZeroSpeed>(1);
  const [paused, _setPaused] = useState<boolean>(false);
  const [mode, setMode] = useState<SimulationMode>(SimulationMode.Server);
  const modeRef = useRef<SimulationMode>(SimulationMode.Server);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  const [scrubSimulationSecond, setScrubSimulationSecond] = useState<number>(0);

  const setSpeed = async (speed: NonZeroSpeed) => {
    const prevSpeed = speedRef.current;
    try {
      speedRef.current = speed;
      _setSpeed(speed);
      if (paused) return;

      if (mode === SimulationMode.Local) {
        await localFrameSourceRef.current.setSpeed(speed);
      } else if (mode === SimulationMode.Server) {
        await serverFrameSourceRef.current?.setSpeed(speed);
      }
    } catch {
      // Revert to previous speed
      speedRef.current = prevSpeed;
      if (prevSpeed !== 0) {
        _setSpeed(prevSpeed);
      }
    }
  };

  const setPaused = async (paused: boolean) => {
    const prevSpeed = speedRef.current;
    try {
      speedRef.current = paused ? 0 : nonZeroSpeed;
      _setPaused(paused);
      if (mode === SimulationMode.Local) {
        await localFrameSourceRef.current.setSpeed(paused ? 0 : nonZeroSpeed);
      } else if (mode === SimulationMode.Server) {
        await serverFrameSourceRef.current?.setSpeed(paused ? 0 : nonZeroSpeed);
      }
    } catch {
      // Revert to previous paused state
      speedRef.current = prevSpeed;
      _setPaused(prevSpeed === 0);
    }
  };

  const scrub = (seconds: number) => {
    // stop sources until scrub is committed
    setMode(SimulationMode.Scrubbing);
    localFrameSourceRef.current.setSpeed(0);
    serverFrameSourceRef.current?.setSpeed(0);
    setScrubSimulationSecond(seconds);

    let targetFrame: BackendPayload | undefined;
    if (seconds === simulationSecondsPassedRef.current) {
      targetFrame = localFrameSourceRef.current.getMaxFrame();
    } else {
      targetFrame = localFrameSourceRef.current.getFrame(seconds);
    }
    if (targetFrame) handleFrame(targetFrame, false);
  };

  const commitScrub = (seconds: number) => {
    // Commit scrub is practically always called from scrubbing state.
    // Under particular circumstances, the simulation provider is not
    // in scrubbing state when commitScrub is called.
    // To account for that case, we force the mode to scrubbing first.
    if (mode !== SimulationMode.Scrubbing) {
      console.warn(
        '[Scrub] commitScrub called outside scrubbing mode, forcing scrubbing mode'
      );
      scrub(seconds);
    } else {
      // Have to set it here cuz if paused, it wont be emitted from frame source
      setScrubSimulationSecond(seconds);
    }

    const scrubToPast = seconds !== simulationSecondsPassedRef.current;

    if (scrubToPast) {
      // Unpause local source to play from scrubbed position
      const frame = localFrameSourceRef.current.getFrame(seconds);
      if (frame) handleFrame(frame, false);
      localFrameSourceRef.current.setPosition(seconds);
      localFrameSourceRef.current.setSpeed(paused ? 0 : nonZeroSpeed);
      setMode(SimulationMode.Local);
    } else if (!scrubToPast) {
      // Unpause server source to play from live position
      const frame = localFrameSourceRef.current.getMaxFrame();
      if (frame) handleFrame(frame, false);
      serverFrameSourceRef.current?.setSpeed(paused ? 0 : nonZeroSpeed);
      setMode(SimulationMode.Server);
    }
  };

  const [simId] = useState<string>(initialSimId);

  // Flag to trigger map render on next animation frame
  const renderOnNextFrameRef = useRef<boolean>(false);

  // RAF queue system for batched map updates
  const mapUpdatePendingRef = useRef<boolean>(false);
  const mapUpdateRafIdRef = useRef<number | null>(null);

  // (TOTAL) NON-REACTIVE SIMULATION ENTITY STATE
  const simulationSecondsRef = useRef<number>(0); // scrub position in seconds
  const simulationSecondsPassedRef = useRef<number>(0); // latest received frame's sim seconds passed
  const [simulationSecondsPassed, setSimulationSecondsPassed] =
    useState<number>(0);

  const startTimeRef = useRef<number>(0);
  const headquartersRef = useRef<Headquarters | null>(null);
  const stationsRef = useRef<Map<number, Station>>(new Map());
  const driversRef = useRef<Map<number, Driver>>(new Map());
  const vehiclesRef = useRef<Map<number, Vehicle>>(new Map());
  const tasksRef = useRef<Map<number, StationTask>>(new Map());

  // (PARTIAL) REACTIVE SIMULATION ENTITY STATE
  const [resourceBarElement, setResourceBarElement] =
    useState<ResourceBarElement>([]);
  const [selectedItem, setSelectedItem] =
    useState<SelectedItemBarElement | null>(null);

  // Since I'm passing the callback to non-reactive classes, need to use a ref instead in handleFrame
  const selectedItemRef = useRef<SelectedItemBarElement | null>(null);
  useEffect(() => {
    selectedItemRef.current = selectedItem;
  }, [selectedItem]);

  const [formattedSimTime, setFormattedSimTime] = useState<string | null>(null);
  const [currentDay, setCurrentDay] = useState<number>(1);

  const [HQWidgetState, setHQWidgetState] = useState<HQWidgetProps>({
    entities: null,
    driversAtHQ: [],
    driversPendingShift: [],
  });

  // Route visualization toggle - using ref to avoid stale closures
  const showAllRoutesRef = useRef<boolean>(false);
  const [showAllRoutes, setShowAllRoutes] = useState<boolean>(false);

  const toggleShowAllRoutes = useCallback(() => {
    const newValue = !showAllRoutesRef.current;
    showAllRoutesRef.current = newValue;
    setShowAllRoutes(newValue);
    // Trigger map update on next frame
    renderOnNextFrameRef.current = true;
  }, []);

  const assignTask = async (driverId: number, taskId: number) => {
    const resource = driversRef.current.get(driverId);

    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = { task_id: taskId, driver_id: driverId };
      await api.post(`/simulation/${simId}/drivers/assign`, payload);

      const updatedResource = resource;
      if (!updatedResource.taskIds.includes(taskId)) {
        updatedResource.taskIds.push(taskId);
      }

      driversRef.current.set(driverId, updatedResource);
      updateResourceBarElement();
      if (selectedItem) {
        updateSelectedItem(selectedItem.value.id, selectedItem.type);
      }
    } catch (error) {
      displayError(
        'Assignment failed',
        'An error occurred while assigning a task to a resource. Please try again later.'
      );
      throw error;
    }
  };

  const unassignTask = async (driverId: number, taskId: number) => {
    const resource = driversRef.current.get(driverId);
    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = { task_id: taskId, driver_id: driverId };
      await api.post(`/simulation/${simId}/drivers/unassign`, payload);

      const updatedResource: Driver = {
        ...resource,
        taskIds: resource.taskIds.filter((t) => t !== taskId),
      };
      driversRef.current.set(driverId, updatedResource);
      updateResourceBarElement();
      if (selectedItem) {
        updateSelectedItem(selectedItem.value.id, selectedItem.type);
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
    prevDriverId: number,
    newDriverId: number,
    taskId: number
  ) => {
    const prevResource = driversRef.current.get(prevDriverId);
    const newResource = driversRef.current.get(newDriverId);
    if (!prevResource) {
      throw new Error(`Previous driver #${prevDriverId} not found.`);
    }
    if (!newResource) {
      throw new Error(`New driver #${newDriverId} not found.`);
    }

    try {
      const payload = {
        task_id: taskId,
        old_driver_id: prevDriverId,
        new_driver_id: newDriverId,
      };

      await api.post(`/simulation/${simId}/drivers/reassign`, payload);

      const updatedPrevResource: Driver = {
        ...prevResource,
        taskIds: prevResource.taskIds.filter((t) => t !== taskId),
      };
      driversRef.current.set(prevDriverId, updatedPrevResource);

      const updatedNewResource = newResource;
      if (!updatedNewResource.taskIds.includes(taskId)) {
        updatedNewResource.taskIds.push(taskId);
      }

      driversRef.current.set(newDriverId, updatedNewResource);
      updateResourceBarElement();
      if (selectedItem) {
        updateSelectedItem(selectedItem.value.id, selectedItem.type);
      }
    } catch (error) {
      displayError(
        'Reassign failed',
        `An error occurred while reassigning task ${taskId} from driver ${prevDriverId} to driver ${newDriverId}. Please try again later.`
      );
      throw error;
    }
  };

  // Reorder tasks within a driver's task queue
  // applyFromTop: if true, insert tasks after in-progress; if false, append to end
  const reorderTasks = async (
    driverId: number,
    taskIds: number[],
    applyFromTop: boolean
  ) => {
    const resource = driversRef.current.get(driverId);
    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = {
        driver_id: driverId,
        task_ids: taskIds,
        apply_from_top: applyFromTop,
      };

      const response = await api.post<{
        driver_id: number;
        task_order: number[];
      }>(`/simulation/${simId}/drivers/reorder-tasks`, payload);

      const updatedResource: Driver = {
        ...resource,
        taskIds: response.data.task_order,
      };
      driversRef.current.set(driverId, updatedResource);
      updateResourceBarElement();
      if (selectedItem) {
        updateSelectedItem(selectedItem.value.id, selectedItem.type);
      }
    } catch (error) {
      displayError(
        'Reorder failed',
        'An error occurred while reordering tasks. Please try again later.'
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
  const frameStartPositionsRef = useRef<Map<number, Position>>(new Map());
  const currentPositionsRef = useRef<Map<number, Position>>(new Map());
  const targetPositionsRef = useRef<Map<number, Position>>(new Map());
  // Route geometry for path-following interpolation
  const routesRef = useRef<Map<number, Route>>(new Map());

  // Last driver update timestamps
  const lastDriverUpdatesRef = useRef<Map<number, number>>(new Map());

  // Animation and cleanup refs
  const animationFrameRef = useRef<number>(0);

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  // Convert WebSocket simulation data to frontend format
  const handlePayload = (
    payload: BackendPayload,
    selectedItem: SelectedItemBarElement | null
  ) => {
    simulationSecondsRef.current = payload.clock.simSecondsPassed;
    startTimeRef.current = payload.clock.startTime;

    // Flags:
    let shouldUpdateReactiveResources = false;

    // Update headquarters (currently happens every frame)
    headquartersRef.current = payload.headquarters;

    // Update tasks that appear in the payload
    if (payload.tasks.length > 0) {
      payload.tasks.forEach((task) => {
        tasksRef.current.set(task.id, task);
        // Task attributes don't meaningfully update - no need to check to update the selectedItem
      });
      renderOnNextFrameRef.current = true;
    }

    // Update stations that appear in the payload
    if (payload.stations.length > 0) {
      payload.stations.forEach((updatedStation: Station) => {
        stationsRef.current.set(updatedStation.id, updatedStation);
        // Update reactive selectedItem if this station is that item
        if (
          selectedItem?.type === SelectedItemType.Station &&
          selectedItem.value.id === updatedStation.id
        ) {
          updateSelectedItem(updatedStation.id, SelectedItemType.Station);
        }
        renderOnNextFrameRef.current = true;
      });
    }

    payload.vehicles.forEach((updatedVehicle: Vehicle) => {
      const existingVehicle = vehiclesRef.current.get(updatedVehicle.id);
      if (vehicleResourceHasUpdated(existingVehicle, updatedVehicle)) {
        shouldUpdateReactiveResources = true;
      }
      vehiclesRef.current.set(updatedVehicle.id, updatedVehicle);
    });

    // Update drivers that appear in the payload
    payload.drivers.forEach((updatedDriver: Driver) => {
      const existingDriver = driversRef.current.get(updatedDriver.id);
      if (driverResourceHasUpdated(existingDriver, updatedDriver)) {
        shouldUpdateReactiveResources = true;
      }

      driversRef.current.set(updatedDriver.id, updatedDriver);

      // Update reactive selectedItem if this resource is that item
      if (
        selectedItem?.type === SelectedItemType.Driver &&
        selectedItem.value.id === updatedDriver.id
      ) {
        updateSelectedItem(updatedDriver.id, SelectedItemType.Driver);
      }
      renderOnNextFrameRef.current = true;
    });

    // Conditionally updating reactive resources list for resource bar
    if (shouldUpdateReactiveResources) {
      updateResourceBarElement();
    }
    updateHQWidgetState();
  };

  // Helper function to update selected resource route display
  const updateSelectedRouteDisplay = (
    selectedResourceId: number | undefined,
    map: mapboxgl.Map
  ) => {
    if (selectedResourceId !== undefined) {
      const route = routesRef.current.get(selectedResourceId);
      const position = currentPositionsRef.current.get(selectedResourceId);
      if (route && position) {
        updateRouteDisplay(
          route.coordinates,
          position,
          route.nextStopIndex,
          map
        );
      } else {
        updateRouteDisplay(null, [0, 0], 0, map);
      }
    } else {
      updateRouteDisplay(null, [0, 0], 0, map);
    }
  };

  // Helper function to update all map sources (hq, stations, resources, and routes)
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

    // Update headquarters
    if (headquartersRef.current) {
      const geojson = adaptHeadquartersToGeoJSON(headquartersRef.current);
      setMapSource(MapSource.Headquarters, geojson, map);
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

    // Update resources - drivers with an assigned vehicle
    if (driversRef.current.size > 0) {
      const resources = Array.from(driversRef.current.values()).filter(
        (driver) => driver.vehicleId !== null
      );
      const geojson = adaptResourcesToGeoJSON(
        resources,
        selectedResourceId,
        hoveredResourceIdRef.current ?? undefined
      );
      setMapSource(MapSource.Resources, geojson, map);
    }

    // Route visualization logic
    if (showAllRoutesRef.current) {
      // Show all routes when toggle is on
      updateAllRoutesDisplay(
        routesRef.current,
        currentPositionsRef.current,
        selectedResourceId,
        map
      );
    } else {
      // Toggle off - clear background routes
      clearAllRoutesDisplay(map);
    }
    // Always show selected route prominently if one is selected
    updateSelectedRouteDisplay(selectedResourceId, map);
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

  const updateSelectedItem = (itemId: number, type: SelectedItemType) => {
    if (type === SelectedItemType.Station) {
      const targetStation = stationsRef.current.get(itemId);
      if (!targetStation) return;
      setSelectedItem({
        type: SelectedItemType.Station,
        value: {
          id: targetStation.id,
          name: targetStation.name,
          position: targetStation.position,
          tasks: targetStation.taskIds.map(
            (taskId: number) => tasksRef.current.get(taskId)!
          ),
        },
      });
      selectedStationIdRef.current = itemId;
      selectedResourceIdRef.current = undefined;
    } else if (type === SelectedItemType.Driver) {
      const targetResource = driversRef.current.get(itemId);
      if (!targetResource) return;
      setSelectedItem({
        type: SelectedItemType.Driver,
        value: {
          id: targetResource.id,
          name: targetResource.name,
          position: targetResource.position,
          tasks: targetResource.taskIds.map(
            (taskId: number) => tasksRef.current.get(taskId)!
          ),
          route: targetResource.route,
          state: targetResource.state,
          inProgressTask: targetResource.inProgressTaskId
            ? tasksRef.current.get(targetResource.inProgressTaskId)!
            : null,
        },
      });
      selectedStationIdRef.current = undefined;
      selectedResourceIdRef.current = itemId;
    }
    queueMapUpdate();
  };

  const updateResourceBarElement = () => {
    setResourceBarElement(
      Array.from(driversRef.current.values())
        .filter((driver) => driver.vehicleId !== null)
        .map((resource) => {
          const vehicle = vehiclesRef.current.get(resource.vehicleId!);

          return {
            id: resource.id,
            name: resource.name,
            taskCount: resource.taskIds.length,
            batteryCount: vehicle!.batteryCount,
            batteryCapacity: vehicle!.batteryCapacity,
          };
        })
    );
  };

  const updateHQWidgetState = () => {
    const newHQState = createHQWidgetState({
      driversMap: driversRef.current,
      vehiclesMap: vehiclesRef.current,
      simulationSeconds: simulationSecondsRef.current,
      startTime: startTimeRef.current,
    });
    setHQWidgetState((prev) => {
      // To minimize re-renders, only update state if there are meaningful changes
      if (areHQWidgetStatesEqual(prev, newHQState)) {
        return prev;
      } else {
        return newHQState;
      }
    });
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
        : driversRef.current.get(id);

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

    updateSelectedItem(id, type);
  };

  // Update hover state with immediate visual feedback
  const updateHoverState = (
    stationId: number | null,
    driverId: number | null
  ) => {
    hoveredStationIdRef.current = stationId;
    hoveredResourceIdRef.current = driverId;

    if (hoverDebounceTimeoutRef.current) {
      clearTimeout(hoverDebounceTimeoutRef.current);
    }

    hoverDebounceTimeoutRef.current = setTimeout(() => {
      queueMapUpdate();
    }, 16); // ~60fps
  };

  // Handle frame updates from WebSocket
  const handleFrame = (payload: BackendPayload, animate = true) => {
    setScrubSimulationSecond(payload.clock.simSecondsPassed);
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

    handlePayload(payload, selectedItemRef.current);

    // For each driver, update the frame start position and target positions
    payload.drivers.forEach((resource: Driver) => {
      const newPosition = resource.position;

      // If we don't wish to animate, set currentPosition directly to newPosition
      if (!animate) {
        currentPositionsRef.current.set(resource.id, newPosition);
        frameStartPositionsRef.current.delete(resource.id);
        targetPositionsRef.current.delete(resource.id);
      }

      const currentPosition = currentPositionsRef.current.get(resource.id);

      // If currentPosition isn't set, initialize it to newPosition
      if (!currentPosition) {
        currentPositionsRef.current.set(resource.id, newPosition);
      }
      // If currentPosition is set and isn't equal to newPosition, we must trigger
      // animation to the new position by setting frame start and target positions
      else if (!positionsEqual(currentPosition, newPosition)) {
        frameStartPositionsRef.current.set(resource.id, currentPosition);
        targetPositionsRef.current.set(resource.id, newPosition);
      }

      // Store route geometry if provided (sent in key frames or when route changes)
      // This is the raw OSRM linestring, not the interpolated points
      if (resource.route?.coordinates) {
        routesRef.current.set(resource.id, {
          coordinates: resource.route.coordinates,
          nextStopIndex: resource.route.nextStopIndex,
        });
      } else if (resource.route === null) {
        // Backend explicitly signals route completion - clear route data
        routesRef.current.delete(resource.id);
      }
      lastDriverUpdatesRef.current.set(resource.id, performance.now());
    });

    // Ensure animation loop is running (in case it stopped)
    ensureAnimationRunning();
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
    // Update position for each resource
    const driverPositionsChanged = updateDriverPositions(
      driversRef.current,
      currentPositionsRef.current,
      frameStartPositionsRef.current,
      targetPositionsRef.current,
      routesRef.current,
      lastDriverUpdatesRef.current,
      speedRef.current
    );
    if (driverPositionsChanged) {
      renderOnNextFrameRef.current = true;
    }

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

  const serverFrameSourceRef = useRef<ServerFrameSource | null>(null);
  const localFrameSourceRef = useRef<LocalFrameSource>(
    new LocalFrameSource(
      simId,
      (frame) => {
        handleFrame(frame);
        if (
          frame.clock.simSecondsPassed === simulationSecondsPassedRef.current
        ) {
          // Reached live simulation point, switch to server mode
          localFrameSourceRef.current.setSpeed(0);
          serverFrameSourceRef.current?.setSpeed(speedRef.current);
          setMode(SimulationMode.Server);
        }
      },
      displayError
    )
  );

  // Derived loading state for convenience
  const [isLoading, setIsLoading] = useState<boolean>(true);
  useEffect(() => {
    if (!serverFrameSourceRef.current)
      serverFrameSourceRef.current = new ServerFrameSource(
        simId,
        (frame) => {
          setStartTime(frame.clock.startTime);
          simulationSecondsPassedRef.current = frame.clock.simSecondsPassed;
          setSimulationSecondsPassed(frame.clock.simSecondsPassed);
          localFrameSourceRef.current.saveFrame(frame);
          if (modeRef.current === SimulationMode.Server) handleFrame(frame);
        },
        displayError
      );
    serverFrameSourceRef.current.start().then(() => {
      setIsLoading(false);
    });
    return () => {
      serverFrameSourceRef.current?.stop();
      localFrameSourceRef.current.setSpeed(0);
    };
  }, []);

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
      } else if (type === SelectedItemType.Driver) {
        updateHoverState(null, id);
      }
    });

    if (stationsRef.current.size > 0 || driversRef.current.size > 0) {
      console.log('[Map] Map loaded, rendering existing data');
      queueMapUpdate();
    }
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

  // ============================================================================
  // CONTEXT PROVIDER
  // ============================================================================

  return (
    <SimulationContext.Provider
      value={{
        speedRef,
        stationsRef,
        driversRef,
        vehiclesRef,
        resourceBarElement,
        selectedItem,
        selectItem,
        clearSelection,
        assignTask,
        unassignTask,
        reassignTask,
        reorderTasks,
        simId,
        isLoading,
        formattedSimTime,
        currentDay,
        HQWidgetState,
        showAllRoutes,
        toggleShowAllRoutes,
        speed: nonZeroSpeed,
        setSpeed,
        paused,
        setPaused,
        scrub,
        commitScrub,
        startTime,
        simulationSecondsPassed,
        scrubSimulationSecond,
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
