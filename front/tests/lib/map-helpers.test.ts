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
  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
  expect(MockMap.instance?.loadImage).toHaveBeenCalledWith(
    '/station.png',
    expect.any(Function)
  );
  expect(MockMap.instance?.loadImage).toHaveBeenCalledWith(
    '/resource.png',
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

  // Should add the resources source with correct configuration
  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('resources', {
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

  expect(MockMap.instance?.addLayer).toHaveBeenCalledTimes(3);
  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'stations',
    type: 'symbol',
    source: 'stations',
    layout: {
      'icon-image': [
        'case',
        ['boolean', ['get', 'selected'], false],
        'station-marker-selected',
        ['boolean', ['get', 'hover'], false],
        'station-marker-hover',
        'station-marker',
      ],
      'icon-allow-overlap': true,
    },
  });

  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'resources',
    type: 'symbol',
    source: 'resources',
    layout: {
      'icon-image': [
        'case',
        ['boolean', ['get', 'selected'], false],
        'resource-marker-selected',
        ['boolean', ['get', 'hover'], false],
        'resource-marker-hover',
        'resource-marker',
      ],
      'icon-allow-overlap': true,
    },
  });
});

test('loadMapImages handles image loading with async callbacks', async () => {
  MockMap.createRandomInstance();

  const mockImage = { width: 32, height: 32 };

  // Mock loadImage to simulate async callback
  MockMap.instance!.loadImage = vi.fn(
    (
      url: string,
      callback: (
        error: Error | null,
        image?: { width: number; height: number }
      ) => void
    ) => {
      // Simulate async image loading
      setTimeout(async () => {
        callback(null, mockImage);
      }, 0);
    }
  );

  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);

  // Wait for async callbacks
  await new Promise((resolve) => setTimeout(resolve, 10));

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
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

test('loadMapImages successfully adds images when loaded', () => {
  MockMap.createRandomInstance();

  const mockImage = { width: 32, height: 32 };

  // Mock loadImage to call the callback with success
  MockMap.instance!.loadImage = vi.fn(
    (
      url: string,
      callback: (
        error: Error | null,
        image?: { width: number; height: number }
      ) => void
    ) => {
      callback(null, mockImage);
    }
  );

  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
  expect(MockMap.instance?.addImage).toHaveBeenCalledTimes(6);
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'station-marker',
    mockImage
  );
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'station-marker-selected',
    mockImage
  );
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'resource-marker',
    mockImage
  );
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'resource-marker-selected',
    mockImage
  );
});

test('loadMapImages handles image load failure gracefully', () => {
  MockMap.createRandomInstance();

  // Mock loadImage to call the callback with an error
  MockMap.instance!.loadImage = vi.fn(
    (
      url: string,
      callback: (
        error: Error | null,
        image?: { width: number; height: number }
      ) => void
    ) => {
      callback(new Error('Failed to load image'));
    }
  );

  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
  // Should not call addImage if loadImage fails
  expect(MockMap.instance?.addImage).not.toHaveBeenCalled();
});
