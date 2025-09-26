import mapboxgl from 'mapbox-gl';
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  type ReactNode,
  type RefObject,
} from 'react';

export const INITIAL_CENTER = [-73.57776, 45.48944] as [number, number];
export const INITIAL_ZOOM = 10.12;

type MapContextType = {
  mapRef: RefObject<mapboxgl.Map | null>;
  mapContainerRef: RefObject<HTMLDivElement | null>;
};

const MapContext = createContext<MapContextType | undefined>(undefined);

export const MapProvider = ({ children }: { children: ReactNode }) => {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;
    mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    mapRef.current = new mapboxgl.Map({
      container: mapContainerRef.current,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
      style: 'mapbox://styles/mahutt/cmfzpcwen001q01sd8d645h3b',
    });

    return () => {
      mapRef.current?.remove();
    };
  }, []);

  return (
    <MapContext.Provider value={{ mapRef, mapContainerRef }}>
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
