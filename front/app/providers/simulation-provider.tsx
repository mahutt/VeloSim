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
import api from '~/api';
import {
  type GetStationsResponse,
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
import { startMockBackend, FRAME_INTERVAL_MS } from '~/lib/mock-backend';
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
} from '~/lib/map-interactions';

type SimulationContextType = {
  stationsRef: React.RefObject<Map<number, Station>>;
  resourcesRef: React.RefObject<Map<number, Resource>>;
  resources: Resource[];
  selectedItem: SelectedItem | null;
  selectItem: (type: SelectedItemType, id: number) => void;
  clearSelection: () => void;
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

export const SimulationProvider = ({ children }: { children: ReactNode }) => {
  const { mapRef, mapLoaded } = useMap();
  const stationsRef = useRef<Map<number, Station>>(new Map());
  const resourcesRef = useRef<Map<number, Resource>>(new Map());

  // Resources state for components that need to react to changes
  const [resources, setResources] = useState<Resource[]>([]);

  // Selection state
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);

  // Selection function
  const selectItem = (type: SelectedItemType, id: number) => {
    if (type === SelectedItemType.Station) {
      const station = stationsRef.current.get(id);
      if (!station) throw new Error('Selected station not found: ' + id);
      setSelectedItem({ type, value: station });
    } else if (type === SelectedItemType.Resource) {
      const resource = resourcesRef.current.get(id);
      if (!resource) throw new Error('Selected resource not found: ' + id);
      setSelectedItem({ type, value: resource });
    }
  };

  // Clear selection function
  const clearSelection = () => {
    setSelectedItem(null);
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
  const stopMockBackendRef = useRef<(() => void) | null>(null);

  // Initialize data loading and animation when map is ready
  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;

    loadStations();
    fetch('/placeholder-data/resources.json')
      .then((res) => res.json())
      .then((data: { resources: Resource[] }) => {
        const resources = data.resources.map((resource) => ({
          id: resource.id,
          position: resource.position,
          taskList: resource.taskList,
          route: {
            coordinates: resource.route.coordinates,
          },
        }));

        resources.forEach((resource) => {
          resourcesRef.current.set(resource.id, resource);
        });

        // Update state so components can react to the loaded resources
        setResources(resources);

        initializeResourcePositions(data.resources);
        startAnimation();
        startBackendSimulation(data.resources);
      })
      .catch((error) => {
        console.error('Error loading resource routes:', error);
      });

    // Set up map click handlers for selection
    setupMapClickHandlers(mapRef.current!, (item) => {
      if (!item) {
        setSelectedItem(null);
        return;
      }
      const { type, id } = item;
      selectItem(type, id);
    });

    // Set up map hover handlers
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

    // Cleanup on unmount
    return cleanup;
  }, [mapLoaded]);

  // Update map and refs when selection changes (not hover)
  useEffect(() => {
    if (!mapLoaded) return;

    // Update refs for animation loop
    if (selectedItem?.type === SelectedItemType.Station) {
      selectedStationIdRef.current = (selectedItem.value as Station).id;
      selectedResourceIdRef.current = undefined;
    } else if (selectedItem?.type === SelectedItemType.Resource) {
      selectedResourceIdRef.current = (selectedItem.value as Resource).id;
      selectedStationIdRef.current = undefined;
    } else {
      selectedStationIdRef.current = undefined;
      selectedResourceIdRef.current = undefined;
    }

    // Re-render stations with selection state (hover handled separately)
    const stations = Array.from(stationsRef.current.values());
    setMapSource(
      MapSource.Stations,
      adaptStationsToGeoJSON(
        stations,
        selectedStationIdRef.current,
        hoveredStationIdRef.current ?? undefined
      ),
      mapRef.current!
    );

    // Force immediate update of resources with current positions
    if (resourcesRef.current.size > 0) {
      const resources = Array.from(resourcesRef.current.values());
      const geojson = adaptResourcesToGeoJSON(
        resources,
        selectedResourceIdRef.current,
        hoveredResourceIdRef.current ?? undefined
      );

      setMapSource(MapSource.Resources, geojson, mapRef.current!);
    }
  }, [selectedItem, mapLoaded]); // Removed hoveredStationId dependency

  // Load station data from backend API
  const loadStations = () => {
    api
      .get<GetStationsResponse>('/stations')
      .then((response) => {
        const stations = response.data.stations.map((station) => ({
          ...station,
          tasks: [], // Initialize empty tasks array until API supports it
        }));

        stations.forEach((station) => {
          stationsRef.current.set(station.id, station);
        });

        setMapSource(
          MapSource.Stations,
          adaptStationsToGeoJSON(stations),
          mapRef.current!
        );
      })
      .catch((error) => {
        console.error('Error fetching stations:', error);
      });
  };

  // Initialize all resources at their route starting positions
  const initializeResourcePositions = (resources: Resource[]) => {
    resources.forEach((resource) => {
      const startPos = resource.route.coordinates[0];
      currentPositionsRef.current.set(resource.id, startPos);
      frameStartPositionsRef.current.set(resource.id, startPos);
      targetPositionsRef.current.set(resource.id, startPos);
    });
  };

  // Start mock backend that emits position updates every second
  const startBackendSimulation = (resources: Resource[]) => {
    stopMockBackendRef.current = startMockBackend(resources, handleFrameUpdate);
  };

  /**
   * TO-DO: Handle position updates from backend frame
   * In #21, this becomes the websocket message handler
   */
  const handleFrameUpdate = (updates: Resource[]) => {
    updates.forEach((update) => {
      // Capture current animated position as start for next interpolation
      const currentAnimatedPos = currentPositionsRef.current.get(update.id);

      if (currentAnimatedPos) {
        frameStartPositionsRef.current.set(update.id, currentAnimatedPos);
      }

      // Set new target position from backend
      targetPositionsRef.current.set(update.id, update.position);

      // Update resource in ref
      resourcesRef.current.set(update.id, update);
    });

    // Reset global frame timer when new frame arrives
    lastFrameTimeRef.current = performance.now();
  };

  // Start animation loop running at 60fps
  const startAnimation = () => {
    lastFrameTimeRef.current = performance.now();

    const animate = (currentTime: number) => {
      updateResourcePositions(currentTime);
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  };

  // Update all resource positions using shared global progress
  // Called 60 times per second by requestAnimationFrame
  const updateResourcePositions = (currentTime: number) => {
    const timeSinceLastFrame = currentTime - lastFrameTimeRef.current;

    // Global progress shared by all resources (0.0 to 1.0 over 1 second)
    const globalProgress = Math.min(
      timeSinceLastFrame / FRAME_INTERVAL_MS,
      1.0
    );

    // Interpolate each resource from frame start to target
    frameStartPositionsRef.current.forEach((startPos, resourceId) => {
      const targetPos = targetPositionsRef.current.get(resourceId);
      const resource = resourcesRef.current.get(resourceId);

      if (!targetPos || !resource) return;

      const routeGeometry = resource.route.coordinates;
      if (!routeGeometry) return;

      // Interpolate along route using global progress
      const interpolatedPos = interpolateAlongRoute(
        routeGeometry,
        startPos, // Where we were when frame arrived
        targetPos, // Where backend says we should be
        globalProgress // Only this changes: 0→1 over 1 second
      );

      // Update current position for next frame's start
      currentPositionsRef.current.set(resourceId, interpolatedPos);

      // Update resource position in ref
      if (resource) {
        resource.position = interpolatedPos;
      }
    });

    // Create GeoJSON from all resources
    const resources = Array.from(resourcesRef.current.values());
    const geojson = adaptResourcesToGeoJSON(
      resources,
      selectedResourceIdRef.current,
      hoveredResourceIdRef.current ?? undefined
    );

    setMapSource(MapSource.Resources, geojson, mapRef.current!);
  };

  // Update hover state with immediate visual feedback
  const updateHoverState = (
    stationId: number | null,
    resourceId: number | null
  ) => {
    // Update refs immediately for cursor changes
    hoveredStationIdRef.current = stationId;
    hoveredResourceIdRef.current = resourceId; // Clear any pending debounced map update
    if (hoverDebounceTimeoutRef.current) {
      clearTimeout(hoverDebounceTimeoutRef.current);
    }

    // Debounce only the expensive map source updates
    hoverDebounceTimeoutRef.current = setTimeout(() => {
      if (!mapRef.current) return;

      // Update stations with hover state
      if (stationsRef.current.size > 0) {
        const stations = Array.from(stationsRef.current.values());
        setMapSource(
          MapSource.Stations,
          adaptStationsToGeoJSON(
            stations,
            selectedStationIdRef.current,
            stationId ?? undefined
          ),
          mapRef.current
        );
      }

      // Update resources with hover state
      if (resourcesRef.current.size > 0) {
        const resources = Array.from(resourcesRef.current.values());
        const geojson = adaptResourcesToGeoJSON(
          resources,
          selectedResourceIdRef.current,
          resourceId ?? undefined
        );
        setMapSource(MapSource.Resources, geojson, mapRef.current);
      }
    }, 16); // ~60fps throttle for map updates only
  };

  // Cleanup animation and mock backend on unmount
  const cleanup = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (stopMockBackendRef.current) {
      stopMockBackendRef.current();
    }
    if (hoverDebounceTimeoutRef.current) {
      clearTimeout(hoverDebounceTimeoutRef.current);
    }
  };

  return (
    <SimulationContext.Provider
      value={{
        stationsRef,
        resourcesRef,
        resources,
        selectedItem,
        selectItem,
        clearSelection,
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
