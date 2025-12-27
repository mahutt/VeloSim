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

import { adaptRouteToGeoJSON } from './geojson-adapters';

export enum MapSource {
  Stations = 'stations',
  Resources = 'resources',
  RouteTraversed = 'route-traversed',
  RouteRemaining = 'route-remaining',
}

export enum MapLayer {
  Stations = 'stations',
  StationTaskCounts = 'station-task-counts',
  Resources = 'resources',
  RouteTraversed = 'route-traversed',
  RouteRemaining = 'route-remaining',
}

export function isMapLayer(value: string): value is MapLayer {
  return (Object.values(MapLayer) as string[]).includes(value);
}

// Setup helpers

/**
 * Helper function to load a single image with error handling
 */
function loadSingleImage(
  map: mapboxgl.Map,
  imagePath: string,
  imageId: string,
  imageType: string
) {
  map.loadImage(imagePath, (error, image) => {
    if (error) {
      console.error(`Failed to load ${imageType}:`, error);
      return;
    }
    map.addImage(imageId, image!);
  });
}

export function loadMapImages(map: mapboxgl.Map) {
  // Define image configurations
  const imageConfigs = [
    // Station images
    {
      path: '/station.png',
      id: 'station-marker',
      type: 'station marker image',
    },
    {
      path: '/station-selected.png',
      id: 'station-marker-selected',
      type: 'station selected marker image',
    },
    {
      path: '/station-hover.png',
      id: 'station-marker-hover',
      type: 'station hover marker image',
    },

    // Resource images
    {
      path: '/resource.png',
      id: 'resource-marker',
      type: 'resource marker image',
    },
    {
      path: '/resource-selected.png',
      id: 'resource-marker-selected',
      type: 'resource selected marker image',
    },
    {
      path: '/resource-hover.png',
      id: 'resource-marker-hover',
      type: 'resource hover marker image',
    },
  ];

  // Load all images using the helper function
  imageConfigs.forEach(({ path, id, type }) => {
    loadSingleImage(map, path, id, type);
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
  // Add route layers first (so they render below markers)
  map.addLayer({
    id: MapLayer.RouteTraversed,
    type: 'line',
    source: MapSource.RouteTraversed,
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#3b82f6',
      'line-width': 4,
      'line-opacity': 0.3,
    },
  });

  map.addLayer({
    id: MapLayer.RouteRemaining,
    type: 'line',
    source: MapSource.RouteRemaining,
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#3b82f6',
      'line-width': 4,
      'line-opacity': 0.8,
    },
  });

  // Add layers for stations
  map.addLayer({
    id: MapLayer.Stations,
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
}

// Setters

export function setMapSource(
  source: MapSource,
  data: GeoJSON.GeoJSON,
  map: mapboxgl.Map
) {
  (map.getSource(source) as mapboxgl.GeoJSONSource).setData(data);
}

/**
 * Update route visualization for a selected resource
 * @param routeGeometry - Full route coordinates (raw OSRM linestring)
 * @param progress - Current progress through route (0-1 fractional)
 * @param map - Mapbox map instance
 */
export function updateRouteDisplay(
  routeGeometry: [number, number][] | null,
  progress: number,
  map: mapboxgl.Map
) {
  const { traversed, remaining } = adaptRouteToGeoJSON(routeGeometry, progress);
  setMapSource(MapSource.RouteTraversed, traversed, map);
  setMapSource(MapSource.RouteRemaining, remaining, map);
}

/**
 * Clear route visualization
 */
export function clearRouteDisplay(map: mapboxgl.Map) {
  updateRouteDisplay(null, 0, map);
}
