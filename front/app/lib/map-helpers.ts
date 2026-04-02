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
import { DriverState, type Position, type Route } from '~/types';
import { adaptRouteToGeoJSON } from './geojson-adapters';

export enum MapSource {
  Headquarters = 'headquarters',
  Stations = 'stations',
  Clusters = 'clusters',
  ClusterCentroids = 'cluster-centroids',
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
  ClusterFills = 'cluster-fills',
  ClusterOutlines = 'cluster-outlines',
  ClusterTaskCounts = 'cluster-task-counts',
  Resources = 'resources',
  RouteNextTask = 'route-next-task',
  RouteFutureTasks = 'route-future-tasks',
  AllRoutesNextTask = 'all-routes-next-task',
}

export function isMapLayer(value: string): value is MapLayer {
  return (Object.values(MapLayer) as string[]).includes(value);
}

const TASK_HOVERED_OR_STATION_SELECTED: ExpressionSpecification = [
  'any',
  ['boolean', ['get', 'taskHover'], false],
  ['boolean', ['get', 'selected'], false],
];

// station is active when hovered on the map, hovered from task list or when selected
const STATION_IS_ACTIVE: ExpressionSpecification = [
  'any',
  ['boolean', ['get', 'hover'], false],
  ['boolean', ['get', 'taskHover'], false],
  ['boolean', ['get', 'selected'], false],
];

function stationRadius(base: number, active: number): ExpressionSpecification {
  return [
    'interpolate',
    ['linear'],
    ['zoom'],
    13,
    ['case', STATION_IS_ACTIVE, active, base],
    17,
    ['case', STATION_IS_ACTIVE, active + 4, base + 4],
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
      path: '/resource-icons/resource-selected.png',
      id: 'resource-marker-selected',
      type: 'resource selected marker image',
    },
    {
      path: '/resource-icons/resource-off-shift.png',
      id: 'resource-marker-off-shift',
      type: 'resource off shift marker image',
    },
    {
      path: '/resource-icons/resource-pending-shift.png',
      id: 'resource-marker-pending-shift',
      type: 'resource pending shift marker image',
    },
    {
      path: '/resource-icons/resource-idle.png',
      id: 'resource-marker-idle',
      type: 'resource idle marker image',
    },
    {
      path: '/resource-icons/resource-on-route.png',
      id: 'resource-marker-on-route',
      type: 'resource on route marker image',
    },
    {
      path: '/resource-icons/resource-servicing.png',
      id: 'resource-marker-servicing',
      type: 'resource servicing marker image',
    },
    {
      path: '/resource-icons/resource-on-break.png',
      id: 'resource-marker-on-break',
      type: 'resource on break marker image',
    },
    {
      path: '/resource-icons/resource-to-restock.png',
      id: 'resource-marker-to-restock',
      type: 'resource to restock marker image',
    },
    {
      path: '/resource-icons/resource-restocking.png',
      id: 'resource-marker-restocking',
      type: 'resource restocking marker image',
    },
    {
      path: '/resource-icons/resource-ending-shift.png',
      id: 'resource-marker-ending-shift',
      type: 'resource ending shift marker image',
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
    filter: ['==', ['get', 'hasPartialAssignment'], true],
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
        TASK_HOVERED_OR_STATION_SELECTED,
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
    filter: TASK_HOVERED_OR_STATION_SELECTED,
  });

  // task count labels for stations
  map.addLayer({
    id: MapLayer.StationTaskCounts,
    type: 'symbol',
    source: MapSource.Stations,
    layout: {
      'text-field': ['get', 'taskCount'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': [
        'interpolate',
        ['linear'],
        ['zoom'],
        8,
        ['case', STATION_IS_ACTIVE, 15, 13],
        17,
        ['case', STATION_IS_ACTIVE, 25, 23],
      ],
      'text-anchor': 'center',
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': [
        'case',
        TASK_HOVERED_OR_STATION_SELECTED,
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
  });

  map.addLayer({
    id: MapLayer.ClusterFills,
    type: 'fill',
    source: MapSource.Clusters,
    paint: {
      'fill-color': [
        'step',
        ['get', 'taskCount'],
        STATION_COLOR_LOW,
        STATION_TASK_COUNT_MEDIUM_THRESHOLD,
        STATION_COLOR_MEDIUM,
        STATION_TASK_COUNT_HIGH_THRESHOLD,
        STATION_COLOR_HIGH,
      ],
      'fill-opacity': ['case', ['boolean', ['get', 'hover'], false], 0.1, 0.2],
    },
  });

  map.addLayer({
    id: MapLayer.ClusterOutlines,
    type: 'line',
    source: MapSource.Clusters,
    paint: {
      'line-color': [
        'step',
        ['get', 'taskCount'],
        STATION_COLOR_LOW,
        STATION_TASK_COUNT_MEDIUM_THRESHOLD,
        STATION_COLOR_MEDIUM,
        STATION_TASK_COUNT_HIGH_THRESHOLD,
        STATION_COLOR_HIGH,
      ],
      'line-width': 2,
      'line-opacity': ['case', ['boolean', ['get', 'hover'], false], 0.5, 1],
    },
  });

  map.addLayer({
    id: MapLayer.ClusterTaskCounts,
    type: 'symbol',
    source: MapSource.ClusterCentroids,
    layout: {
      'text-field': ['get', 'taskCount'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 8, 13, 17, 23],
      'text-anchor': 'center',
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': [
        'step',
        ['get', 'taskCount'],
        STATION_COLOR_LOW,
        STATION_TASK_COUNT_MEDIUM_THRESHOLD,
        STATION_COLOR_MEDIUM,
        STATION_TASK_COUNT_HIGH_THRESHOLD,
        STATION_COLOR_HIGH,
      ],
      'text-halo-color': 'rgba(0, 0, 0, 0)',
      'text-halo-width': 0,
      'text-opacity': ['case', ['boolean', ['get', 'hover'], false], 0.5, 1],
    },
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
        [
          'match',
          ['get', 'state'],
          DriverState.OffShift,
          'resource-marker-off-shift',
          DriverState.PendingShift,
          'resource-marker-pending-shift',
          DriverState.Idle,
          'resource-marker-idle',
          DriverState.OnRoute,
          'resource-marker-on-route',
          DriverState.ServicingStation,
          'resource-marker-servicing',
          DriverState.OnBreak,
          'resource-marker-on-break',
          DriverState.SeekingHQForInventory,
          'resource-marker-to-restock',
          DriverState.RestockingBatteries,
          'resource-marker-restocking',
          DriverState.EndingShift,
          'resource-marker-ending-shift',
          'resource-marker-off-shift',
        ],
      ],

      'icon-allow-overlap': true,
      'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.5, 13, 1.0],
      'text-field': ['get', 'name'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 10, 8, 15, 12],
      'text-offset': [0, -1.5],
      'text-anchor': 'bottom',
      'text-allow-overlap': true,
      'icon-rotate': ['get', 'bearing'],
      'icon-rotation-alignment': 'map',
      'icon-pitch-alignment': 'map',
    },
    paint: {
      'icon-opacity': [
        'case',
        ['boolean', ['get', 'selected'], false],
        1,
        ['boolean', ['get', 'hover'], false],
        0.7,
        1,
      ],
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

/**
 * Compute an entity's bearing (orientation) from its current and target positions
 *
 * Formula adapted from https://www.movable-type.co.uk/scripts/latlong.html
 *
 * @param current - current position as [longitude, latitude]
 * @param target - target position as [longitude, latitude]
 * @returns bearing in degrees (0-360, where 0/360 is north, 90 is east, etc.)
 */
export function computeBearing(current: Position, target: Position): number {
  const λ1 = (current[0] * Math.PI) / 180;
  const φ1 = (current[1] * Math.PI) / 180;
  const λ2 = (target[0] * Math.PI) / 180;
  const φ2 = (target[1] * Math.PI) / 180;

  const y = Math.sin(λ2 - λ1) * Math.cos(φ2);
  const x =
    Math.cos(φ1) * Math.sin(φ2) -
    Math.sin(φ1) * Math.cos(φ2) * Math.cos(λ2 - λ1);
  const θ = Math.atan2(y, x);
  return ((θ * 180) / Math.PI + 360) % 360;
}
