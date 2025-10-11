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
  type Route,
  type Resource,
  type SelectedItem,
  SelectedItemType,
} from '~/types';
import { adaptStationsToGeoJSON } from '~/lib/geojson-adapters';
import { interpolateAlongRoute } from '~/lib/animation-helpers';
import { startMockBackend, FRAME_INTERVAL_MS } from '~/lib/mock-backend';
import { setupMapClickHandlers } from '~/lib/map-interactions';

type SimulationContextType = {
  stationsRef: React.RefObject<Map<number, Station>>;
  resourcesRef: React.RefObject<Map<number, Resource>>;
  selectedItem: SelectedItem | null;
  selectItem: (type: SelectedItemType, id: number) => void;
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

export const SimulationProvider = ({ children }: { children: ReactNode }) => {
  const { mapRef, mapLoaded } = useMap();
  const stationsRef = useRef<Map<number, Station>>(new Map());
  const resourcesRef = useRef<Map<number, Resource>>(new Map());

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

  // Route geometries (received once, stored for interpolation)
  const routeGeometriesRef = useRef<Map<number, [number, number][]>>(new Map());

  // Position tracking for each resource
  const frameStartPositionsRef = useRef<Map<number, [number, number]>>(
    new Map()
  );
  const currentPositionsRef = useRef<Map<number, [number, number]>>(new Map());
  const targetPositionsRef = useRef<Map<number, [number, number]>>(new Map());
  const resourceRoutesRef = useRef<Map<number, number>>(new Map());

  // Global frame timing (shared by all resources)
  const lastFrameTimeRef = useRef<number>(0);

  // Animation and cleanup refs
  const animationFrameRef = useRef<number>(0);
  const stopMockBackendRef = useRef<(() => void) | null>(null);

  // Initialize data loading and animation when map is ready
  useEffect(() => {
    if (!mapLoaded) return;

    loadStations();
    fetch('/placeholder-data/resources.json')
      .then((res) => res.json())
      .then((data: { resources: Resource[] }) => {
        data.resources.forEach((resource) => {
          resourcesRef.current.set(resource.id, resource);
        });

        // Auto-selects first resource (if available) to render the resources
        if (data.resources.length > 0) {
          selectItem(SelectedItemType.Resource, data.resources[0].id);
        }
        const routes: Route[] = data.resources.map((resource) => ({
          id: resource.id,
          coordinates: resource.route.coordinates,
        }));

        // Store route geometries for interpolation
        routes.forEach((route) => {
          routeGeometriesRef.current.set(route.id, route.coordinates);
        });

        initializeResourcePositions(routes);
        startAnimation();
        startBackendSimulation(routes);
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

    // Cleanup on unmount
    return cleanup;
  }, [mapLoaded]);

  // TODO: Remove useEffect when UI is implemented
  useEffect(() => {
    console.log('Selected item changed:', selectedItem);
  }, [selectedItem]);

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
  const initializeResourcePositions = (routes: Route[]) => {
    routes.forEach((route) => {
      const startPos = route.coordinates[0];
      currentPositionsRef.current.set(route.id, startPos);
      frameStartPositionsRef.current.set(route.id, startPos);
      targetPositionsRef.current.set(route.id, startPos);
      resourceRoutesRef.current.set(route.id, route.id);
    });
  };

  // Start mock backend that emits position updates every second
  const startBackendSimulation = (routes: Route[]) => {
    stopMockBackendRef.current = startMockBackend(routes, handleFrameUpdate);
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
      resourceRoutesRef.current.set(update.id, update.id);
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

    const features: GeoJSON.Feature[] = [];

    // Interpolate each resource from frame start to target
    frameStartPositionsRef.current.forEach((startPos, resourceId) => {
      const targetPos = targetPositionsRef.current.get(resourceId);
      const routeId = resourceRoutesRef.current.get(resourceId);

      if (!targetPos || !routeId) return;

      const routeGeometry = routeGeometriesRef.current.get(routeId);
      if (!routeGeometry) return;

      // Interpolate along route using global progress
      const interpolatedPos = interpolateAlongRoute(
        routeGeometry,
        startPos, // Where we were when frame arrive
        targetPos, // Where backend says we should be
        globalProgress // Only this changes: 0→1 over 1 second
      );

      // Update current position for next frame's start
      currentPositionsRef.current.set(resourceId, interpolatedPos);

      features.push({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: interpolatedPos,
        },
        properties: { id: resourceId },
      });
    });

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features,
    };

    setMapSource(MapSource.Resources, geojson, mapRef.current!);
  };

  // Cleanup animation and mock backend on unmount
  const cleanup = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (stopMockBackendRef.current) {
      stopMockBackendRef.current();
    }
  };

  return (
    <SimulationContext.Provider
      value={{
        stationsRef,
        resourcesRef,
        selectedItem,
        selectItem,
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
