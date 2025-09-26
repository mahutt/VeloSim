import { expect, test } from 'vitest';
import { render } from '@testing-library/react';
import {
  INITIAL_CENTER,
  INITIAL_ZOOM,
  MapProvider,
} from '~/providers/map-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';

test('map provider instantiates mapboxgl Map instance in presence of map container', async () => {
  render(
    <MapProvider>
      <MapContainer />
    </MapProvider>
  );
  const map = MockMap.instance;
  expect(map).toBeDefined();
  expect(map!.getCenter()).toBe(INITIAL_CENTER);
  expect(map!.getZoom()).toBe(INITIAL_ZOOM);
});

test("map provider doesn't instantiate mapboxgl Map instance without map container", async () => {
  render(
    <MapProvider>
      <div />
    </MapProvider>
  );
  const map = MockMap.instance;
  expect(map).toBeUndefined();
});
