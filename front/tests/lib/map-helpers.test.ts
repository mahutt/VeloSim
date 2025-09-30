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

import { expect, test, vi } from 'vitest';
import {
  loadMapImages,
  initializeMapSources,
  setMapLayers,
  setMapSource,
  MapSource,
} from '~/lib/map-helpers';
import { MockMap } from 'tests/mocks';

test('loadMapImages loads all necessary images', () => {
  MockMap.createRandomInstance();
  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);
  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(1);
  expect(MockMap.instance?.loadImage).toHaveBeenCalledWith(
    '/station.png',
    expect.any(Function)
  );
});

test('initializeMapSources adds all required sources', () => {
  MockMap.createRandomInstance();
  initializeMapSources(MockMap.instance! as unknown as mapboxgl.Map);

  // Should add one source for each MapSource enum value
  expect(MockMap.instance?.addSource).toHaveBeenCalledTimes(
    Object.values(MapSource).length
  );

  // Should add the stations source with correct configuration
  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('stations', {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features: [],
    },
  });
});

test('setMapLayers adds stations layer with correct configuration', () => {
  MockMap.createRandomInstance();
  setMapLayers(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.addLayer).toHaveBeenCalledTimes(1);
  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'stations',
    type: 'symbol',
    source: 'stations',
    layout: {
      'icon-image': 'station-marker',
      'icon-allow-overlap': true,
    },
  });
});

test('setMapSource updates source data correctly', () => {
  MockMap.createRandomInstance();

  // Mock the getSource method to return an object with setData method
  const mockGeoJSONSource = {
    setData: vi.fn(),
  };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const testData: GeoJSON.GeoJSON = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [-73.935242, 40.73061],
        },
        properties: {
          name: 'Test Station',
        },
      },
    ],
  };

  setMapSource(
    MapSource.Stations,
    testData,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('stations');
  expect(mockGeoJSONSource.setData).toHaveBeenCalledWith(testData);
});
