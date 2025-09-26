import 'mapbox-gl/dist/mapbox-gl.css';
import MapContainer from '~/components/map/map-container';
import { MapProvider } from '~/providers/map-provider';

export function meta() {
  return [{ title: 'Simulation' }];
}

export default function Simulation() {
  return (
    <>
      <MapProvider>
        <MapContainer />
      </MapProvider>
    </>
  );
}
