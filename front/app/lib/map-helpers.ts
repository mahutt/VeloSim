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

export enum MapSource {
  Stations = 'stations',
  Resources = 'resources',
}

export enum MapLayer {
  Stations = 'stations',
  StationTaskCounts = 'station-task-counts',
  Resources = 'resources',
}

export function isMapLayer(value: string): value is MapLayer {
  return (Object.values(MapLayer) as string[]).includes(value);
}

// Setup helpers

export function loadMapImages(map: mapboxgl.Map) {
  // Load station image
  map.loadImage('/station.png', async (error, image) => {
    if (error) throw error;
    map.addImage('station-marker', image!);
  });

  // Load resource image
  map.loadImage('/resource.png', async (error, image) => {
    if (error) throw error;
    map.addImage('resource-marker', image!);
  });
}

export function initializeMapSources(map: mapboxgl.Map) {
  Object.values(MapSource).forEach((source) => {
    map.addSource(source, {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [],
      },
    });
  });
}

export function setMapLayers(map: mapboxgl.Map) {
  // Add layers for stations
  map.addLayer({
    id: MapLayer.Stations,
    type: 'symbol',
    source: 'stations',
    layout: {
      'icon-image': 'station-marker',
      'icon-allow-overlap': true,
    },
  });

  // Add task count labels above stations
  map.addLayer({
    id: MapLayer.StationTaskCounts,
    type: 'symbol',
    source: 'stations',
    layout: {
      'text-field': ['get', 'taskCount'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': 12,
      'text-offset': [0, -2],
      'text-anchor': 'bottom',
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': '#ffffff',
      'text-halo-color': '#000000',
      'text-halo-width': 2,
    },
  });

  // Add layers for resources
  map.addLayer({
    id: MapLayer.Resources,
    type: 'symbol',
    source: 'resources',
    layout: {
      'icon-image': 'resource-marker',
      'icon-allow-overlap': true,
    },
  });
}

// Setters

export function setMapSource(
  source: MapSource,
  data: GeoJSON.GeoJSON,
  map: mapboxgl.Map
) {
  (map.getSource(source) as mapboxgl.GeoJSONSource).setData(data);
}
