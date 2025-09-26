import { useMap } from '~/providers/map-provider';

export default function MapContainer() {
  const { mapContainerRef } = useMap();
  return (
    <div
      id="map-container"
      data-testid="map-container"
      className="h-screen w-full"
      ref={mapContainerRef}
    />
  );
}
