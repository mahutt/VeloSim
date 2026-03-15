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
  EMPTY_FEATURE_COLLECTION,
  FREE_FLOW_COLOR,
  ROUTE_LINE_OFFSET,
  ROUTE_LINE_WIDTH,
  STATION_COLOR_LOW,
  STATION_COLOR_MEDIUM,
  STATION_COLOR_HIGH,
  STATION_COLOR_LOW_HOVERED,
  STATION_COLOR_MEDIUM_HOVERED,
  STATION_COLOR_HIGH_HOVERED,
  STATION_RING_COLOR_LOW,
  STATION_RING_COLOR_MEDIUM,
  STATION_RING_COLOR_HIGH,
  STATION_TASK_COUNT_MEDIUM_THRESHOLD,
  STATION_TASK_COUNT_HIGH_THRESHOLD,
} from '~/constants';
import type { ExpressionSpecification } from 'mapbox-gl';
import type { Position, Route } from '~/types';
import { adaptRouteToGeoJSON } from './geojson-adapters';

export enum MapSource {
  Headquarters = 'headquarters',
  Stations = 'stations',
  Resources = 'resources',
  RouteNextTask = 'route-next-task',
  RouteFutureTasks = 'route-future-tasks',
  AllRoutesNextTask = 'all-routes-next-task',
}

export enum MapLayer {
  Headquarters = 'headquarters',
  Stations = 'stations',
  StationCircle = 'station-circle',
  StationRing = 'station-ring',
  StationTaskCounts = 'station-task-counts',
  Resources = 'resources',
  RouteNextTask = 'route-next-task',
  RouteFutureTasks = 'route-future-tasks',
  AllRoutesNextTask = 'all-routes-next-task',
}

export function isMapLayer(value: string): value is MapLayer {
  return (Object.values(MapLayer) as string[]).includes(value);
}

const IS_HOVERED_OR_SELECTED: ExpressionSpecification = [
  'any',
  ['boolean', ['get', 'hover'], false],
  ['boolean', ['get', 'selected'], false],
];

function stationRadius(base: number, active: number): ExpressionSpecification {
  return [
    'interpolate',
    ['linear'],
    ['zoom'],
    13,
    ['case', IS_HOVERED_OR_SELECTED, active, base],
    17,
    ['case', IS_HOVERED_OR_SELECTED, active + 4, base + 4],
  ];
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

    // HQ image
    {
      path: '/hq.png',
      id: 'hq-marker',
      type: 'headquarters marker image',
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
  // All routes layers (faded background routes when toggle is on)
  // Background routes layer (only next task shown for clarity)
  map.addLayer({
    id: MapLayer.AllRoutesNextTask,
    type: 'line',
    source: MapSource.AllRoutesNextTask,
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': ['coalesce', ['get', 'color'], FREE_FLOW_COLOR],
      'line-width': ROUTE_LINE_WIDTH,
      'line-opacity': 0.35,
      'line-offset': ROUTE_LINE_OFFSET,
    },
  });

  // Selected route layers (prominent on top)
  map.addLayer({
    id: MapLayer.RouteNextTask,
    type: 'line',
    source: MapSource.RouteNextTask,
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': ['coalesce', ['get', 'color'], FREE_FLOW_COLOR],
      'line-width': ROUTE_LINE_WIDTH,
      'line-opacity': ['coalesce', ['get', 'opacity'], 0.9],
      'line-offset': ROUTE_LINE_OFFSET,
    },
  });

  map.addLayer({
    id: MapLayer.RouteFutureTasks,
    type: 'line',
    source: MapSource.RouteFutureTasks,
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': ['coalesce', ['get', 'color'], FREE_FLOW_COLOR],
      'line-width': ROUTE_LINE_WIDTH,
      'line-opacity': [
        'number',
        ['*', ['coalesce', ['get', 'opacity'], 0.9], 0.45],
        0.4,
      ],
      'line-offset': ROUTE_LINE_OFFSET,
    },
  });

  // circles for stations zoomed out
  map.addLayer({
    id: MapLayer.StationCircle,
    type: 'circle',
    source: MapSource.Stations,
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['get', 'taskCount'],
        0,
        2, // no tasks = 2px radius
        3,
        5, // 3+ tasks = 5px radius
      ],
      'circle-color': [
        'step',
        ['get', 'taskCount'],
        STATION_COLOR_LOW,
        STATION_TASK_COUNT_MEDIUM_THRESHOLD,
        STATION_COLOR_MEDIUM,
        STATION_TASK_COUNT_HIGH_THRESHOLD,
        STATION_COLOR_HIGH,
      ],
    },
    maxzoom: 13,
    filter: ['>', ['get', 'taskCount'], 0],
  });

  // ring for stations that have partial assignment
  map.addLayer({
    id: MapLayer.StationRing,
    type: 'circle',
    source: MapSource.Stations,
    paint: {
      'circle-radius': stationRadius(12, 13),
      'circle-color': 'rgba(0, 0, 0, 0)',
      'circle-stroke-color': [
        'step',
        ['get', 'taskCount'],
        STATION_RING_COLOR_LOW,
        STATION_TASK_COUNT_MEDIUM_THRESHOLD,
        STATION_RING_COLOR_MEDIUM,
        STATION_TASK_COUNT_HIGH_THRESHOLD,
        STATION_RING_COLOR_HIGH,
      ],
      'circle-stroke-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        8,
        1.5,
        13,
        2,
        17,
        2.5,
      ],
    },
    minzoom: 13,
    filter: [
      'all',
      ['>', ['get', 'taskCount'], 0],
      ['==', ['get', 'hasPartialAssignment'], true],
    ],
  });

  // Add layers for stations (filtered to only show stations with taskCount > 0)
  map.addLayer({
    id: MapLayer.Stations,
    type: 'circle',
    source: MapSource.Stations,
    paint: {
      'circle-radius': stationRadius(11, 12),
      'circle-color': [
        'case',
        ['boolean', ['get', 'selected'], false],
        [
          'step',
          ['get', 'taskCount'],
          STATION_COLOR_LOW,
          STATION_TASK_COUNT_MEDIUM_THRESHOLD,
          STATION_COLOR_MEDIUM,
          STATION_TASK_COUNT_HIGH_THRESHOLD,
          STATION_COLOR_HIGH,
        ],
        'rgba(0, 0, 0, 0)',
      ],
    },
    minzoom: 13,
    filter: ['>', ['get', 'taskCount'], 0],
  });

  // Add task count labels above stations (filtered to only show stations with taskCount > 0)
  map.addLayer({
    id: MapLayer.StationTaskCounts,
    type: 'symbol',
    source: MapSource.Stations,
    layout: {
      'text-field': ['get', 'taskCount'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 8, 13, 17, 23],
      'text-anchor': 'center',
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': [
        'case',
        ['boolean', ['get', 'selected'], false],
        '#ffffff',
        ['boolean', ['get', 'hover'], false],
        [
          'step',
          ['get', 'taskCount'],
          STATION_COLOR_LOW_HOVERED,
          STATION_TASK_COUNT_MEDIUM_THRESHOLD,
          STATION_COLOR_MEDIUM_HOVERED,
          STATION_TASK_COUNT_HIGH_THRESHOLD,
          STATION_COLOR_HIGH_HOVERED,
        ],
        [
          'step',
          ['get', 'taskCount'],
          STATION_COLOR_LOW,
          STATION_TASK_COUNT_MEDIUM_THRESHOLD,
          STATION_COLOR_MEDIUM,
          STATION_TASK_COUNT_HIGH_THRESHOLD,
          STATION_COLOR_HIGH,
        ],
      ],
      'text-halo-color': 'rgba(0, 0, 0, 0)',
      'text-halo-width': 0,
    },
    minzoom: 13,
    filter: ['>', ['get', 'taskCount'], 0],
  });

  // Add layer for headquarters
  map.addLayer({
    id: MapLayer.Headquarters,
    type: 'symbol',
    source: MapSource.Headquarters,
    layout: {
      'icon-image': 'hq-marker',
      'icon-allow-overlap': true,
      'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.5, 13, 1.0],
    },
  });

  // Add layers for resources
  map.addLayer({
    id: MapLayer.Resources,
    type: 'symbol',
    source: MapSource.Resources,
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
      'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.5, 13, 1.0],
      'text-field': ['get', 'name'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 10, 8, 15, 12],
      'text-offset': [0, -1.5],
      'text-anchor': 'bottom',
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': '#000000',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1,
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
 * Render provided route on the provided Mapbox map instance
 * @param route - Route object containing coordinates, nextStopIndex, and optional trafficRanges
 * @param position - Current driver position
 * @param map - Mapbox map instance
 */
export function updateRouteDisplay(
  route: Route,
  position: Position,
  map: mapboxgl.Map
) {
  const { nextTask, futureTasks } = adaptRouteToGeoJSON(route, position);
  setMapSource(MapSource.RouteNextTask, nextTask, map);
  setMapSource(MapSource.RouteFutureTasks, futureTasks, map);
}

/**
 * Clear route visualization
 */
export function clearRouteDisplay(map: mapboxgl.Map) {
  setMapSource(MapSource.RouteNextTask, EMPTY_FEATURE_COLLECTION, map);
  setMapSource(MapSource.RouteFutureTasks, EMPTY_FEATURE_COLLECTION, map);
}

/**
 * Update all routes visualization (for background display when toggle is on)
 * Shows only the next task route for each vehicle to reduce visual clutter.
 * The selected vehicle's full route is displayed on a separate, more prominent layer.
 *
 * @param routes - Map of driver IDs to their routes
 * @param positions - Map of driver IDs to their current positions
 * @param selectedDriverId - ID of selected driver (to exclude from all-routes layer)
 * @param map - Mapbox map instance
 */
export function updateAllRoutesDisplay(
  routes: Map<number, Route>,
  positions: Map<number, Position>,
  selectedDriverId: number | null,
  map: mapboxgl.Map
) {
  const allNextTaskFeatures: GeoJSON.Feature[] = [];

  routes.forEach((route, driverId) => {
    // Skip selected driver's route (it's shown prominently on separate layer)
    if (driverId === selectedDriverId) return;

    const position = positions.get(driverId);
    if (!position) return;

    // Validate route data
    if (!route.coordinates || route.coordinates.length === 0) return;

    const { nextTask } = adaptRouteToGeoJSON(route, position);

    // Only show next task for background routes (reduces visual clutter)
    allNextTaskFeatures.push(...nextTask.features);
  });

  setMapSource(
    MapSource.AllRoutesNextTask,
    {
      type: 'FeatureCollection',
      features: allNextTaskFeatures,
    },
    map
  );
}

/**
 * Clear all routes visualization
 * Removes all background route displays from the map
 *
 * @param map - Mapbox map instance
 */
export function clearAllRoutesDisplay(map: mapboxgl.Map) {
  setMapSource(MapSource.AllRoutesNextTask, EMPTY_FEATURE_COLLECTION, map);
}
