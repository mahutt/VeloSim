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
  ResourcePosition,
  ResourceRoute,
} from '~/types';
import { adaptStationsToGeoJSON } from '~/lib/geojson-adapters';
import { interpolatePosition } from '~/lib/animation-helpers';

type SimulationContextType = {
  state: React.RefObject<Station[]>;
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

export const SimulationProvider = ({ children }: { children: ReactNode }) => {
  const { mapRef, mapLoaded } = useMap();
  const state = useRef<Station[]>([]);
  const resourcePositionsRef = useRef<ResourcePosition[]>([]);
  const routesRef = useRef<ResourceRoute[]>([]);
  const animationFrameRef = useRef<number>(0);
  const lastUpdateTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!mapLoaded) return;

    // Load stations
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

    // Load and animate resources
    fetch('/placeholder-data/resource-routes.geojson')
      .then((res) => res.json())
      .then((data: GeoJSON.FeatureCollection) => {
        const routes: ResourceRoute[] = data.features.map((feature) => ({
          id: feature.properties?.id,
          coordinates: (feature.geometry as GeoJSON.LineString).coordinates as [
            number,
            number,
          ][],
        }));

        routesRef.current = routes;

        // Initialize resource positions at first waypoint
        resourcePositionsRef.current = routes.map((route) => ({
          id: route.id,
          position: route.coordinates[0],
          currentWaypointIndex: 0,
          progress: 0,
        }));

        // Start animation loop
        lastUpdateTimeRef.current = performance.now();
        const animate = (currentTime: number) => {
          updateResourcePositions(currentTime);
          animationFrameRef.current = requestAnimationFrame(animate);
        };
        animationFrameRef.current = requestAnimationFrame(animate);
      });

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [mapLoaded]);

  const updateResourcePositions = (currentTime: number) => {
    const deltaTime = currentTime - lastUpdateTimeRef.current;
    lastUpdateTimeRef.current = currentTime;

    // Placeholder timing for local animation until backend integration
    const segmentDurationMs = 3000;
    const fps = 60;
    const speedPerFrame = 1 / ((segmentDurationMs / 1000) * fps);
    const adjustedSpeed = speedPerFrame * (deltaTime / (1000 / fps));

    resourcePositionsRef.current = resourcePositionsRef.current.map(
      (resource) => {
        const route = routesRef.current.find((r) => r.id === resource.id)!;
        let { currentWaypointIndex, progress } = resource;

        progress += adjustedSpeed;

        if (progress >= 1) {
          progress = 0;
          currentWaypointIndex =
            (currentWaypointIndex + 1) % (route.coordinates.length - 1);
        }

        const start = route.coordinates[currentWaypointIndex];
        const end = route.coordinates[currentWaypointIndex + 1];
        const position = interpolatePosition(start, end, progress);

        return {
          ...resource,
          position,
          currentWaypointIndex,
          progress,
        };
      }
    );

    // Update map with new positions
    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: resourcePositionsRef.current.map((resource) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: resource.position,
        },
        properties: {
          id: resource.id,
        },
      })),
    };

    if (mapRef.current?.getSource(MapSource.Resources)) {
      setMapSource(MapSource.Resources, geojson, mapRef.current);
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
