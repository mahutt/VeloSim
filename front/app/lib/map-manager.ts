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

import type { Map as MapboxGLMap } from 'mapbox-gl';
import type {
  BackendPayload,
  Driver,
  Headquarters,
  Position,
  Route,
  Station,
} from '~/types';
import {
  adaptHeadquartersToGeoJSON,
  adaptStationsToGeoJSON,
  adaptResourcesToGeoJSON,
  adaptClustersToGeoJSON,
  adaptClusterCentroidsToGeoJSON,
} from './geojson-adapters';
import {
  setMapSource,
  MapSource,
  MapLayer,
  updateAllRoutesDisplay,
  clearAllRoutesDisplay,
  updateRouteDisplay,
  clearRouteDisplay,
  computeBearing,
} from './map-helpers';
import {
  setupMapClickHandlers,
  setupMapDropHandlers,
  setupMapHoverHandlers,
  setupStationDragHandlers,
  setupBoxSelectHandlers,
} from '~/lib/map-interactions';
import { SelectedItemType } from '~/components/map/selected-item-bar';
import { positionsEqual } from './utils';
import type SimulationStateManager from './simulation-state-manager';
import { updateDriverPositions } from './animation-helpers';
import { toast } from 'sonner';
import { log, LogContext, LogLevel } from './logger';
import { featureCollection } from '@turf/helpers';
import type { Feature, Point } from 'geojson';
import { GLOBAL_BOUNDS } from '~/constants';
import Supercluster from 'supercluster';

export default class MapManager {
  private map: MapboxGLMap;
  private state: SimulationStateManager;

  // locals
  private hoveredStationId: number | null;
  private taskHoveredStationId: number | null;
  private hoveredResourceId: number | null;
  private hoveredClusterId: number | null;
  private hoverDebounceTimeout: NodeJS.Timeout | null;
  private hoverLocked: boolean;

  // for animations
  private currentPositions: Map<number, Position>;
  private frameStartPositions: Map<number, Position>;
  private targetPositions: Map<number, Position>;
  private bearings: Map<number, number>;
  private routes: Map<number, Route>;
  private lastDriverUpdates: Map<number, number>;
  private animationFrame: number;

  // for clustering
  private clusters: Map<number, Feature<Point>>;
  private supercluster: Supercluster;
  private quantizedZoom: number;

  constructor(
    map: MapboxGLMap,
    state: SimulationStateManager,
    selectItem: (type: SelectedItemType, id: number) => void,
    requestAssignment: (resourceId: number, taskIds: number[]) => void
  ) {
    this.map = map;
    this.state = state;

    this.hoveredStationId = null;
    this.taskHoveredStationId = null;
    this.hoveredResourceId = null;
    this.hoveredClusterId = null;
    this.hoverDebounceTimeout = null;
    this.hoverLocked = false;

    this.currentPositions = new Map();
    this.frameStartPositions = new Map();
    this.targetPositions = new Map();
    this.bearings = new Map();
    this.routes = new Map();
    this.lastDriverUpdates = new Map();
    this.animationFrame = 0;

    this.clusters = new Map();
    this.supercluster = new Supercluster({
      maxZoom: 13,
      minZoom: 11,
      map: (props) => ({
        taskCount: props!.taskCount,
        stationIds: [props!.id],
      }),
      reduce: (accumulated, props) => {
        accumulated!.taskCount += props!.taskCount;
        accumulated!.stationIds = accumulated!.stationIds.concat(
          props!.stationIds
        );
      },
    });
    this.quantizedZoom = Math.floor(this.map.getZoom());

    map.on('zoom', () => {
      const newQuantizedZoom = Math.floor(map.getZoom());
      if (this.quantizedZoom === newQuantizedZoom) return;
      this.quantizedZoom = newQuantizedZoom;
      this.updateStationAndClusterSources();
    });

    setupMapClickHandlers(
      map,
      (item, modifiers) => {
        if (!item) {
          this.state.clearSelection();
          return;
        }

        // Ctrl+click on a station toggles multi-selection
        if (modifiers!.ctrlKey && item.type === SelectedItemType.Station) {
          // If a single station was selected, promote it into the multi-selection
          const selectedItems = this.state.getSelectedItems();
          if (
            selectedItems.length === 1 &&
            selectedItems[0].type === SelectedItemType.Station
          ) {
            const singleStationId = selectedItems[0].value.id;
            this.state.clearSelection();
            if (!this.state.getMultiSelectedStationIds().has(singleStationId)) {
              this.state.addSelectedStation(singleStationId);
            }
          }
          this.state.toggleSelectedStation(item.id);

          // If only 1 station left, demote back to single selection
          const remaining = this.state.getMultiSelectedStationIds();
          if (remaining.size <= 1) {
            const lastId = remaining.values().next().value;
            this.state.clearSelection();
            if (remaining.size === 1 && lastId !== undefined) {
              selectItem(SelectedItemType.Station, lastId);
            }
          }
          return;
        }

        // Regular click clears multi-selection and selects single item
        this.state.clearSelection();
        const { type, id } = item;
        selectItem(type, id);
      },
      this.onClusterClick.bind(this)
    );

    setupMapHoverHandlers(map, (item) => {
      if (!item) {
        this.updateHoverState(null, null, null);
        return;
      }
      const { type, id } = item;
      if (type === SelectedItemType.Station) {
        this.updateHoverState(id, null, null);
      } else if (type === SelectedItemType.Driver) {
        this.updateHoverState(null, id, null);
      }
    });

    setupMapDropHandlers(map, requestAssignment);

    setupBoxSelectHandlers(
      map,
      [MapLayer.Stations, MapLayer.StationCircle, MapLayer.StationTaskCounts],
      (stationIds) => {
        if (stationIds.length > 1) {
          this.state.clearSelection();
          this.state.setSelectedStations(stationIds);
        } else if (stationIds.length === 1) {
          this.state.clearSelection();
          selectItem(SelectedItemType.Station, stationIds[0]);
        }
      }
    );

    setupStationDragHandlers(
      map,
      state,
      (stationIds, driverId) => {
        const driver = this.state.getDriver(driverId);
        if (!driver) {
          toast.error(`Driver #${driverId} not found.`);
          log({
            message: `Failed to drag stations onto driver #${driverId} because driver was not found`,
            level: LogLevel.ERROR,
            context: LogContext.StationDragDrop,
          });
          return;
        }

        const allTaskIds: number[] = [];

        for (const sid of stationIds) {
          const station = this.state.getStation(sid);
          if (!station) {
            toast.error(`Station #${sid} not found.`);
            log({
              message: `Failed to drag station #${sid} onto driver because station was not found`,
              level: LogLevel.ERROR,
              context: LogContext.StationDragDrop,
            });
            continue;
          }
          allTaskIds.push(...station.taskIds);
        }

        if (allTaskIds.length === 0) {
          if (stationIds.length === 1) {
            const station = this.state.getStation(stationIds[0]);
            toast.info(
              `No tasks at ${station?.name ?? `station #${stationIds[0]}`}.`
            );
          } else {
            toast.info(`No tasks at the selected stations.`);
          }
          return;
        }

        requestAssignment(driverId, allTaskIds);
        log({
          message: `Dragged ${stationIds.length} station(s) onto driver #${driverId} to assign ${allTaskIds.length} tasks`,
          level: LogLevel.INFO,
          context: LogContext.StationDragDrop,
        });
      },
      (stationId, clusterId) => {
        if (stationId !== null || clusterId !== null) {
          this.updateHoverState(stationId, null, clusterId);
          this.hoverLocked = true;
        } else {
          this.hoverLocked = false;
          this.updateHoverState(null, null, null);
        }
      },
      () => Array.from(this.state.getMultiSelectedStationIds()),
      (stationId) => {
        // When drag actually starts, select the dragged station if it
        // wasn't already part of the current selection.
        if (!this.state.getMultiSelectedStationIds().has(stationId)) {
          this.state.setSelectedItem(this.state.getStation(stationId) ?? null);
        }
      },
      (stationId) => {
        const station = this.state.getStation(stationId);
        return station?.taskIds.length ?? 0;
      }
    );

    this.animationFrame = requestAnimationFrame(() => this.animateResources());
  }

  public processFrame(payload: BackendPayload, animate: boolean) {
    payload.drivers.forEach((resource: Driver) => {
      const newPosition = resource.position;

      // If we don't wish to animate, set currentPosition directly to newPosition
      if (!animate) {
        this.currentPositions.set(resource.id, newPosition);
        this.frameStartPositions.delete(resource.id);
        this.targetPositions.delete(resource.id);
      }

      const currentPosition = this.currentPositions.get(resource.id);

      // If currentPosition isn't set, initialize it to newPosition
      if (!currentPosition) {
        this.currentPositions.set(resource.id, newPosition);
      }
      // If currentPosition is set and isn't equal to newPosition, we must trigger
      // animation to the new position by setting frame start and target positions
      else if (!positionsEqual(currentPosition, newPosition)) {
        this.frameStartPositions.set(resource.id, currentPosition);
        this.targetPositions.set(resource.id, newPosition);
        this.bearings.set(
          resource.id,
          computeBearing(currentPosition, newPosition)
        );
      }

      // Store route geometry if provided (sent in key frames or when route changes)
      // This is the raw routing linestring, not the interpolated points
      if (resource.route?.coordinates) {
        this.routes.set(resource.id, resource.route);
      } else if (resource.route === null) {
        // Backend explicitly signals route completion - clear route data
        this.routes.delete(resource.id);
      }
      this.lastDriverUpdates.set(resource.id, performance.now());
    });
  }

  private animateResources() {
    // Update position for each resource
    const driverPositionsChanged = updateDriverPositions(
      this.state.getAllDrivers(),
      this.currentPositions,
      this.frameStartPositions,
      this.targetPositions,
      this.routes,
      this.lastDriverUpdates,
      this.state.getNonZeroSpeed()
    );
    if (driverPositionsChanged) {
      this.state.setMapShouldRefresh(true);
    }

    // Only update map if positions or station tasks changed
    if (this.state.getMapShouldRefresh()) {
      // Call updateMapSources directly since we're already in a RAF callback
      this.updateMapSources(
        this.state.getShowAllRoutes(),
        this.state.getAllDrivers(),
        this.state.getAllStations(),
        this.routes,
        this.currentPositions,
        this.state.getHeadquarters()
      );

      this.state.setMapShouldRefresh(false);
    }

    // Continue animation loop
    this.animationFrame = requestAnimationFrame(() => this.animateResources());
  }

  public updateMapSources(
    showAllRoutes: boolean,
    drivers: Driver[],
    stations: Station[],
    routesMap: Map<number, Route>,
    currentPositionsMap: Map<number, Position>,
    headquarters: Headquarters | null
  ) {
    const map = this.map;

    // Check if map style is loaded
    if (!map.isStyleLoaded()) {
      map.once('styledata', () => {
        this.updateMapSources(
          showAllRoutes,
          drivers,
          stations,
          routesMap,
          currentPositionsMap,
          headquarters
        );
      });
      return;
    }

    // Update headquarters
    if (headquarters) {
      const geojson = adaptHeadquartersToGeoJSON(headquarters);
      setMapSource(MapSource.Headquarters, geojson, map);
    }

    // Update stations
    if (stations.length > 0) {
      const geojson = adaptStationsToGeoJSON(
        stations.filter((s) => s.taskIds.length > 0),
        this.state.getMultiSelectedStationIds(),
        this.hoveredStationId,
        this.taskHoveredStationId,
        this.state.getPartialAssignmentStationIds()
      );
      this.supercluster.load(geojson.features);
      this.updateStationAndClusterSources();
    }

    // Derive selected resource (driver) ID from selection state
    const selectedItems = this.state.getSelectedItems();
    const selectedResourceId =
      selectedItems.length === 1 &&
      selectedItems[0].type === SelectedItemType.Driver
        ? selectedItems[0].value.id
        : null;

    // Update resources - drivers with an assigned vehicle
    if (drivers.length > 0) {
      const resources = drivers.filter((driver) => driver.vehicleId !== null);
      const geojson = adaptResourcesToGeoJSON(
        resources,
        selectedResourceId,
        this.hoveredResourceId,
        this.bearings
      );
      setMapSource(MapSource.Resources, geojson, map);
    }

    // Route visualization logic
    if (showAllRoutes) {
      // Show all routes when toggle is on
      updateAllRoutesDisplay(
        routesMap,
        currentPositionsMap,
        selectedResourceId,
        map
      );
    } else {
      // Toggle off - clear background routes
      clearAllRoutesDisplay(map);
    }
    // Always show selected route prominently if one is selected
    this.updateSelectedRouteDisplay(
      selectedResourceId,
      map,
      routesMap,
      currentPositionsMap
    );
  }

  public cleanup() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
  }

  private updateSelectedRouteDisplay(
    selectedDriverId: number | null,
    map: mapboxgl.Map,
    routes: Map<number, Route>,
    currentPositions: Map<number, Position>
  ) {
    if (selectedDriverId === null) {
      clearRouteDisplay(map);
      return;
    }
    const route = routes.get(selectedDriverId);
    const position = currentPositions.get(selectedDriverId);
    if (route && position) {
      updateRouteDisplay(route, position, map);
    } else {
      clearRouteDisplay(map);
    }
  }

  public setTaskHoveredStationId(stationId: number | null) {
    this.taskHoveredStationId = stationId;
    this.state.setMapShouldRefresh(true);
  }

  private updateHoverState(
    stationId: number | null,
    driverId: number | null,
    clusterId: number | null
  ) {
    if (this.hoverLocked) {
      return;
    }
    this.hoveredStationId = stationId;
    this.hoveredResourceId = driverId;
    this.hoveredClusterId = clusterId;

    if (this.hoverDebounceTimeout) {
      clearTimeout(this.hoverDebounceTimeout);
    }

    this.hoverDebounceTimeout = setTimeout(() => {
      this.state.setMapShouldRefresh(true);
    }, 16); // ~60fps
  }

  private updateStationAndClusterSources() {
    const clusters: Feature<Point>[] = [];
    const stations: Feature<Point>[] = [];

    for (const feature of this.supercluster.getClusters(
      GLOBAL_BOUNDS,
      this.map.getZoom()
    )) {
      (feature.properties?.cluster_id ? clusters : stations).push(feature);
    }
    clusters.forEach((c) =>
      this.clusters.set(c.properties!.cluster_id as number, c)
    );

    setMapSource(MapSource.Stations, featureCollection(stations), this.map);

    clusters.forEach((c) => {
      const stationPoints = (c.properties!.stationIds as number[]).map(
        (stationId: number) => this.state.getStation(stationId)!.position
      );
      c.properties!.stationPoints = stationPoints;
    });
    setMapSource(
      MapSource.Clusters,
      adaptClustersToGeoJSON(clusters, this.hoveredClusterId),
      this.map
    );
    setMapSource(
      MapSource.ClusterCentroids,
      adaptClusterCentroidsToGeoJSON(clusters, this.hoveredClusterId),
      this.map
    );
  }

  private onClusterClick(clusterId: number) {
    const cluster = this.clusters.get(clusterId);
    if (!cluster) return;
    const targetZoom = this.supercluster.getClusterExpansionZoom(clusterId);
    this.map.easeTo({
      center: {
        lng: cluster.geometry.coordinates[0],
        lat: cluster.geometry.coordinates[1],
      },
      zoom: targetZoom,
    });
  }
}
