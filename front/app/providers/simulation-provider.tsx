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
  type ReactNode,
} from 'react';

import { useMap } from './map-provider';
import { MapSource, setMapSource } from '~/lib/map-helpers';
import api from '~/api';
import type {
  GetStationsResponse,
  Station,
  Route,
  ResourcePosition,
} from '~/types';
import { adaptStationsToGeoJSON } from '~/lib/geojson-adapters';
import { interpolateAlongRoute } from '~/lib/animation-helpers';
import { startMockBackend, FRAME_INTERVAL_MS } from '~/lib/mock-backend';

type SimulationContextType = {
  state: React.RefObject<Station[]>;
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

export const SimulationProvider = ({ children }: { children: ReactNode }) => {
  const { mapRef, mapLoaded } = useMap();
  const state = useRef<Station[]>([]);

  // Route geometries (received once, stored for interpolation)
  const routeGeometriesRef = useRef<Map<string, [number, number][]>>(new Map());

  // Position tracking for each resource
  const currentPositionsRef = useRef<Map<string, [number, number]>>(new Map());
  const targetPositionsRef = useRef<Map<string, [number, number]>>(new Map());
  const resourceRoutesRef = useRef<Map<string, string>>(new Map());

  // Global frame timing
  const lastFrameTimeRef = useRef<number>(0);

  // Animation and cleanup refs
  const animationFrameRef = useRef<number>(0);
  const stopMockBackendRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!mapLoaded) return;

    loadStations();
    loadAndAnimateResources();

    return cleanup;
  }, [mapLoaded]);

  const loadStations = () => {
    api
      .get<GetStationsResponse>('/stations')
      .then((response) => {
        const stations = response.data.stations;
        state.current = stations;
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

  const loadAndAnimateResources = () => {
    fetch('/placeholder-data/resource-routes.geojson')
      .then((res) => res.json())
      .then((data: GeoJSON.FeatureCollection) => {
        const routes: Route[] = data.features.map((feature) => ({
          id: feature.properties?.id,
          coordinates: (feature.geometry as GeoJSON.LineString).coordinates as [
            number,
            number,
          ][],
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
  };

  const initializeResourcePositions = (routes: Route[]) => {
    routes.forEach((route) => {
      const startPos = route.coordinates[0];
      currentPositionsRef.current.set(route.id, startPos);
      targetPositionsRef.current.set(route.id, startPos);
      resourceRoutesRef.current.set(route.id, route.id);
    });
  };

  const startBackendSimulation = (routes: Route[]) => {
    stopMockBackendRef.current = startMockBackend(routes, handleFrameUpdate);
  };

  /**
   * TO-DO: Handle position updates from backend frame
   * In #21, this becomes the websocket message handler
   */
  const handleFrameUpdate = (updates: ResourcePosition[]) => {
    updates.forEach((update) => {
      targetPositionsRef.current.set(update.resourceId, update.position);
      resourceRoutesRef.current.set(update.resourceId, update.routeId);
    });

    // Reset global frame timer when new frame arrives
    lastFrameTimeRef.current = performance.now();
  };

  const startAnimation = () => {
    lastFrameTimeRef.current = performance.now();

    const animate = (currentTime: number) => {
      updateResourcePositions(currentTime);
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);
  };

  const updateResourcePositions = (currentTime: number) => {
    const timeSinceLastFrame = currentTime - lastFrameTimeRef.current;

    // Clamped to 1.0 to avoid overshooting if frames are delayed
    const globalProgress = Math.min(
      timeSinceLastFrame / FRAME_INTERVAL_MS,
      1.0
    );

    const features: GeoJSON.Feature[] = [];

    currentPositionsRef.current.forEach((currentPos, resourceId) => {
      const targetPos = targetPositionsRef.current.get(resourceId);
      const routeId = resourceRoutesRef.current.get(resourceId);

      if (!targetPos || !routeId) return;

      const routeGeometry = routeGeometriesRef.current.get(routeId);
      if (!routeGeometry) return;

      // Interpolate position along route geometry
      const interpolatedPos = interpolateAlongRoute(
        routeGeometry,
        currentPos,
        targetPos,
        globalProgress
      );

      // Update current position for next frame
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

  const cleanup = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (stopMockBackendRef.current) {
      stopMockBackendRef.current();
    }
  };

  return (
    <SimulationContext.Provider value={{ state }}>
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
