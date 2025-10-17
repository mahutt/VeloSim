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

import mapboxgl from 'mapbox-gl';
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from 'react';
import {
  initializeMapSources,
  loadMapImages,
  setMapLayers,
} from '~/lib/map-helpers';

export const INITIAL_CENTER = [-73.57776, 45.48944] as [number, number];
export const INITIAL_ZOOM = 10.12;

type MapContextType = {
  mapRef: RefObject<mapboxgl.Map | null>;
  mapContainerRef: RefObject<HTMLDivElement | null>;
  mapLoaded: boolean;
};

const MapContext = createContext<MapContextType | undefined>(undefined);

export const MapProvider = ({ children }: { children: ReactNode }) => {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    if (!mapContainerRef.current) return;
    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      style: 'mapbox://styles/mahutt/cmfzpcwen001q01sd8d645h3b',
    });

    mapRef.current.on('load', () => {
      if (!mapRef.current) return;
      loadMapImages(mapRef.current);
      initializeMapSources(mapRef.current);
      setMapLayers(mapRef.current);
      setMapLoaded(true);
    });

    // Force the map to resize when the container size changes
    const handleResize = () => {
      mapRef.current?.resize();
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(mapContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      mapRef.current?.remove();
    };
  }, []);

  return (
    <MapContext.Provider value={{ mapRef, mapContainerRef, mapLoaded }}>
      {children}
    </MapContext.Provider>
  );
};

export const useMap = (): MapContextType => {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error('useMap must be used within a MapProvider');
  }
  return context;
};
