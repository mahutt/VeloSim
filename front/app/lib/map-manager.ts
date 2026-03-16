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
} from './geojson-adapters';
import {
  setMapSource,
  MapSource,
  MapLayer,
  updateAllRoutesDisplay,
  clearAllRoutesDisplay,
  updateRouteDisplay,
  clearRouteDisplay,
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
import { log, LogLevel } from './logger';

export default class MapManager {
  private map: MapboxGLMap;
  private state: SimulationStateManager;

  // locals
  private hoveredStationId: number | null;
  private hoveredResourceId: number | null;
  private hoverDebounceTimeout: NodeJS.Timeout | null;
  private hoverLocked: boolean;

  // for animations
  private currentPositions: Map<number, Position>;
  private frameStartPositions: Map<number, Position>;
  private targetPositions: Map<number, Position>;
  private routes: Map<number, Route>;
  private lastDriverUpdates: Map<number, number>;
  private animationFrame: number;

  constructor(
    map: MapboxGLMap,
    state: SimulationStateManager,
    selectItem: (type: SelectedItemType, id: number) => void,
    requestAssignment: (resourceId: number, taskIds: number[]) => void
  ) {
    this.map = map;
    this.state = state;

    this.hoveredStationId = null;
    this.hoveredResourceId = null;
    this.hoverDebounceTimeout = null;
    this.hoverLocked = false;

    this.currentPositions = new Map();
    this.frameStartPositions = new Map();
    this.targetPositions = new Map();
    this.routes = new Map();
    this.lastDriverUpdates = new Map();
    this.animationFrame = 0;

    setupMapClickHandlers(map, (item, modifiers) => {
      if (!item) {
        this.state.clearSelection();
        return;
      }

      // Ctrl+click on a station toggles multi-selection
      if (modifiers!.ctrlKey && item.type === SelectedItemType.Station) {
        // If a single station was selected, promote it into the multi-selection
        const currentSingle = this.state.getSelectedItem();
        if (this.isStation(currentSingle)) {
          const singleStationId = currentSingle.id;
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
    });

    setupMapHoverHandlers(map, (item) => {
      if (!item) {
        this.updateHoverState(null, null);
        return;
      }
      const { type, id } = item;
      if (type === SelectedItemType.Station) {
        this.updateHoverState(id, null);
      } else if (type === SelectedItemType.Driver) {
        this.updateHoverState(null, id);
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
      (stationIds, driverId) => {
        const driver = this.state.getDriver(driverId);
        if (!driver) {
          toast.error(`Driver #${driverId} not found.`);
          log({
            message: `Failed to drag stations onto driver #${driverId} because driver was not found`,
            level: LogLevel.ERROR,
            context: 'station_drag_drop',
          });
          return;
        }

        const allTaskIds: number[] = [];
        const stationNames: string[] = [];

        for (const sid of stationIds) {
          const station = this.state.getStation(sid);
          if (!station) {
            toast.error(`Station #${sid} not found.`);
            log({
              message: `Failed to drag station #${sid} onto driver because station was not found`,
              level: LogLevel.ERROR,
              context: 'station_drag_drop',
            });
            continue;
          }
          allTaskIds.push(...station.taskIds);
          stationNames.push(station.name);
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
          context: 'station_drag_drop',
        });
      },
      (stationId) => {
        if (stationId !== null) {
          this.updateHoverState(stationId, null);
          this.hoverLocked = true;
        } else {
          this.hoverLocked = false;
          this.updateHoverState(null, null);
        }
      },
      () => Array.from(this.state.getMultiSelectedStationIds()),
      (stationId) => {
        // When drag actually starts, select the dragged station if it
        // wasn't already part of the current selection.
        if (!this.state.getMultiSelectedStationIds().has(stationId)) {
          this.state.setSelectedItem(this.state.getStation(stationId) ?? null);
        }
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
      }

      // Store route geometry if provided (sent in key frames or when route changes)
      // This is the raw OSRM linestring, not the interpolated points
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
        stations,
        this.getSelectedStationId(),
        this.hoveredStationId ?? undefined,
        this.state.getMultiSelectedStationIds()
      );
      setMapSource(MapSource.Stations, geojson, map);
    }

    // Update resources - drivers with an assigned vehicle
    if (drivers.length > 0) {
      const resources = drivers.filter((driver) => driver.vehicleId !== null);
      const geojson = adaptResourcesToGeoJSON(
        resources,
        this.getSelectedResourceId(),
        this.hoveredResourceId ?? undefined
      );
      setMapSource(MapSource.Resources, geojson, map);
    }

    // Route visualization logic
    if (showAllRoutes) {
      // Show all routes when toggle is on
      updateAllRoutesDisplay(
        routesMap,
        currentPositionsMap,
        this.getSelectedResourceId(),
        map
      );
    } else {
      // Toggle off - clear background routes
      clearAllRoutesDisplay(map);
    }
    // Always show selected route prominently if one is selected
    this.updateSelectedRouteDisplay(
      this.getSelectedResourceId(),
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
    selectedDriverId: number | undefined,
    map: mapboxgl.Map,
    routes: Map<number, Route>,
    currentPositions: Map<number, Position>
  ) {
    if (selectedDriverId === undefined) {
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

  private updateHoverState(stationId: number | null, driverId: number | null) {
    if (this.hoverLocked) {
      return;
    }
    this.hoveredStationId = stationId;
    this.hoveredResourceId = driverId;

    if (this.hoverDebounceTimeout) {
      clearTimeout(this.hoverDebounceTimeout);
    }

    this.hoverDebounceTimeout = setTimeout(() => {
      this.state.setMapShouldRefresh(true);
    }, 16); // ~60fps
  }

  private getSelectedStationId(): number | undefined {
    const selectedItem = this.state.getSelectedItem();
    return this.isStation(selectedItem) ? selectedItem.id : undefined;
  }

  private getSelectedResourceId(): number | undefined {
    const selectedItem = this.state.getSelectedItem();
    return this.isDriver(selectedItem) ? selectedItem.id : undefined;
  }

  private isStation(item: Driver | Station | null): item is Station {
    return item !== null && !('shift' in item);
  }

  private isDriver(item: Driver | Station | null): item is Driver {
    return item !== null && 'shift' in item;
  }
}
