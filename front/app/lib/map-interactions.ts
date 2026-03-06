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

import type { Map as MapboxMap, MapMouseEvent } from 'mapbox-gl';
import { isMapLayer, MapLayer } from './map-helpers';
import { SelectedItemType } from '~/components/map/selected-item-bar';
import type { Position } from '~/types';

// Entities may be represented by more than 1 layer (e.g., stations and their task counts)
// So we use a function to map layers to entity types
function layerToEntityType(layer: MapLayer): SelectedItemType | null {
  switch (layer) {
    case MapLayer.Stations:
    case MapLayer.StationTaskCounts:
      return SelectedItemType.Station;
    case MapLayer.Resources:
      return SelectedItemType.Driver;
    default:
      return null;
  }
}

// Set up click handlers for map layers to enable item selection
type ItemSelectCallback = (
  item: {
    type: SelectedItemType;
    id: number;
    coordinates: Position;
  } | null,
  modifiers?: { ctrlKey: boolean }
) => void;

type ItemHoverCallback = (
  item: {
    type: SelectedItemType;
    id: number;
  } | null
) => void;

export function setupMapClickHandlers(
  map: MapboxMap,
  onItemSelect: ItemSelectCallback
) {
  map.on('click', (e: MapMouseEvent) => {
    const modifiers = {
      ctrlKey: e.originalEvent?.ctrlKey || e.originalEvent?.metaKey || false,
    };
    const features = map.queryRenderedFeatures(e.point, {
      layers: Object.values(MapLayer),
    });

    if (features.length === 0) {
      onItemSelect(null, modifiers);
      return;
    }

    const feature = features[0];

    if (!feature.properties || !feature.properties.id) {
      throw new Error('Clicked feature has no id property');
    }

    if (!feature.layer || !isMapLayer(feature.layer.id)) {
      throw new Error('Clicked feature is not from a recognized layer');
    }

    const type = layerToEntityType(feature.layer.id);
    if (type === null) return;

    const id = Number(feature.properties.id);
    const coordinates = (feature.geometry as GeoJSON.Point).coordinates as [
      number,
      number,
    ];

    onItemSelect({ type, id, coordinates }, modifiers);
  });

  Object.values(MapLayer).forEach((layer) => {
    map.on('mouseenter', layer, () => {
      map.getCanvas().style.cursor = 'pointer';
    });

    map.on('mouseleave', layer, () => {
      map.getCanvas().style.cursor = '';
    });
  });
}

export function setupMapHoverHandlers(
  map: MapboxMap,
  onItemHover: ItemHoverCallback
) {
  Object.values(MapLayer).forEach((layer) => {
    map.on('mousemove', layer, (e) => {
      if (e.features && e.features.length > 0) {
        const id = e.features[0].properties?.id;
        if (id !== undefined) {
          const type = layerToEntityType(layer);
          if (type === null) return;
          onItemHover({
            type,
            id: Number(id),
          });
        }
      }
    });

    map.on('mouseleave', layer, () => {
      onItemHover(null);
    });
  });
}

export function setupMapDropHandlers(
  map: MapboxMap,
  requestAssignment: (resourceId: number, taskIds: number[]) => void
) {
  const canvas = map.getCanvas();

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'move';
    }
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    if (!e.dataTransfer) return;

    const taskIdsPayload = e.dataTransfer.getData('taskIds');
    let taskIds: number[] = [];
    if (taskIdsPayload) {
      try {
        taskIds = JSON.parse(taskIdsPayload || '[]');
      } catch {
        return;
      }
    }

    if (taskIds.length === 0) return;

    // covert drop position from viewport to the canvas' coordinates
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const features = map.queryRenderedFeatures([x, y], {
      layers: [MapLayer.Resources],
    });

    if (!features || features.length === 0) return;

    const feature = features[0];
    const resourceId = Number(feature.properties?.id);
    if (Number.isNaN(resourceId)) return;

    requestAssignment(resourceId, taskIds);
  };

  canvas.addEventListener('dragover', handleDragOver);
  canvas.addEventListener('drop', handleDrop);

  return () => {
    canvas.removeEventListener('dragover', handleDragOver);
    canvas.removeEventListener('drop', handleDrop);
  };
}

// Minimum pixel movement before entering drag mode (so clicks still work)
const DRAG_THRESHOLD = 5;

// DOM-based drag ghost that floats above all overlays
const GHOST_WIDTH = 28;

function createDomGhost(stationCount = 1): HTMLElement {
  if (stationCount <= 1) {
    const img = document.createElement('img');
    img.src = '/station-selected.png';
    img.setAttribute('data-testid', 'station-drag-ghost');
    Object.assign(img.style, {
      position: 'fixed',
      width: `${GHOST_WIDTH}px`,
      height: 'auto',
      pointerEvents: 'none',
      zIndex: '9999',
      opacity: '0.85',
      transform: 'translate(-50%, -50%)',
    });
    document.body.appendChild(img);
    return img;
  }

  const container = document.createElement('div');
  container.setAttribute('data-testid', 'station-drag-ghost');
  Object.assign(container.style, {
    position: 'fixed',
    pointerEvents: 'none',
    zIndex: '9999',
    transform: 'translate(-50%, -50%)',
  });

  const img = document.createElement('img');
  img.src = '/station-selected.png';
  Object.assign(img.style, {
    width: `${GHOST_WIDTH}px`,
    height: 'auto',
    opacity: '0.85',
  });
  container.appendChild(img);

  const badge = document.createElement('span');
  badge.textContent = String(stationCount);
  badge.setAttribute('data-testid', 'station-drag-badge');
  Object.assign(badge.style, {
    position: 'absolute',
    top: '-6px',
    right: '-8px',
    backgroundColor: '#3b82f6',
    color: 'white',
    borderRadius: '50%',
    width: '18px',
    height: '18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: 'bold',
  });
  container.appendChild(badge);

  document.body.appendChild(container);
  return container;
}

function moveDomGhost(ghost: HTMLElement, x: number, y: number) {
  ghost.style.left = `${x}px`;
  ghost.style.top = `${y}px`;
}

function removeDomGhost(ghost: HTMLElement | null) {
  ghost?.remove();
}

export type StationDragDropCallback = (
  stationIds: number[],
  driverId: number
) => void;

/**
 * Set up box-select for stations via Shift+drag.
 * Disables Mapbox's built-in boxZoom and draws a selection rectangle.
 * On release, queries all station features within the rectangle.
 */
export function setupBoxSelectHandlers(
  map: MapboxMap,
  stationLayers: string[],
  onBoxSelect: (stationIds: number[]) => void
) {
  map.boxZoom.disable();

  let boxSelectActive = false;
  let startPoint: { x: number; y: number } | null = null;
  let boxElement: HTMLDivElement | null = null;

  function createBoxElement(): HTMLDivElement {
    const div = document.createElement('div');
    div.setAttribute('data-testid', 'box-select-overlay');
    Object.assign(div.style, {
      position: 'absolute',
      border: '2px dashed #3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      pointerEvents: 'none',
      zIndex: '1',
    });
    map.getCanvas().parentElement?.appendChild(div);
    return div;
  }

  function updateBoxElement(
    box: HTMLDivElement,
    start: { x: number; y: number },
    end: { x: number; y: number }
  ) {
    const left = Math.min(start.x, end.x);
    const top = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    box.style.left = `${left}px`;
    box.style.top = `${top}px`;
    box.style.width = `${width}px`;
    box.style.height = `${height}px`;
  }

  function removeBoxElement() {
    boxElement?.remove();
    boxElement = null;
  }

  function cleanup() {
    removeBoxElement();
    boxSelectActive = false;
    startPoint = null;
    map.dragPan.enable();
    map.getCanvas().style.cursor = '';
  }

  function onMouseDown(e: MapMouseEvent) {
    if (!e.originalEvent?.shiftKey) return;

    e.preventDefault();
    startPoint = { x: e.point.x, y: e.point.y };
    boxSelectActive = true;
    map.dragPan.disable();
    map.getCanvas().style.cursor = 'crosshair';
  }

  function onMouseMove(e: MapMouseEvent) {
    if (!boxSelectActive || !startPoint) return;

    if (!boxElement) {
      boxElement = createBoxElement();
    }
    updateBoxElement(boxElement, startPoint, {
      x: e.point.x,
      y: e.point.y,
    });
  }

  function onMouseUp(e: MapMouseEvent) {
    if (!boxSelectActive || !startPoint) return;

    const minX = Math.min(startPoint.x, e.point.x);
    const minY = Math.min(startPoint.y, e.point.y);
    const maxX = Math.max(startPoint.x, e.point.x);
    const maxY = Math.max(startPoint.y, e.point.y);

    const features = map.queryRenderedFeatures(
      [
        [minX, minY],
        [maxX, maxY],
      ],
      { layers: stationLayers }
    );

    const stationIds = features
      .map((f) => Number(f.properties?.id))
      .filter((id) => !Number.isNaN(id));

    const uniqueIds = Array.from(new Set(stationIds));

    if (uniqueIds.length > 0) {
      onBoxSelect(uniqueIds);
    }

    cleanup();
  }

  map.on('mousedown', onMouseDown);
  map.on('mousemove', onMouseMove);
  map.on('mouseup', onMouseUp);

  return () => {
    map.off('mousedown', onMouseDown);
    map.off('mousemove', onMouseMove);
    map.off('mouseup', onMouseUp);
    cleanup();
  };
}

/**
 * Set up map-level station drag handlers.
 * Long-press / mousedown on a station icon, drag to a driver icon, release to
 * trigger `onDrop(stationIds, driverId)`.
 * Supports multi-station drag when stations are multi-selected.
 */
export function setupStationDragHandlers(
  map: MapboxMap,
  onDrop: StationDragDropCallback,
  onHighlight?: (stationId: number | null) => void,
  getMultiSelectedStationIds?: () => number[]
) {
  let dragging = false;
  let stationId: number | null = null;
  let draggedStationIds: number[] = [];
  let originLngLat: [number, number] | null = null;
  let startPoint: { x: number; y: number } | null = null;
  let thresholdMet = false;
  let hoveredDriverId: number | null = null;
  let wasDragPanEnabled: boolean | null = null;
  let domGhost: HTMLElement | null = null;

  const stationLayers = [MapLayer.Stations, MapLayer.StationCircle];

  function cleanup() {
    dragging = false;
    stationId = null;
    draggedStationIds = [];
    originLngLat = null;
    startPoint = null;
    thresholdMet = false;
    hoveredDriverId = null;
    removeDomGhost(domGhost);
    domGhost = null;
    onHighlight?.(null);
    if (wasDragPanEnabled !== null) {
      if (wasDragPanEnabled) {
        map.dragPan.enable();
      } else {
        map.dragPan.disable();
      }
      wasDragPanEnabled = null;
    }
    map.getCanvas().style.cursor = '';
  }

  function onMouseDown(e: MapMouseEvent) {
    // Shift+drag is reserved for box select
    if (e.originalEvent?.shiftKey) return;

    const features = map.queryRenderedFeatures(e.point, {
      layers: stationLayers,
    });
    if (!features || features.length === 0) return;

    const feature = features[0];
    const id = feature.properties?.id;
    if (id === undefined) return;

    stationId = Number(id);

    // Determine which stations to drag: if the clicked station is part of
    // multi-selection, drag all selected stations; otherwise just this one.
    const multiIds = getMultiSelectedStationIds?.() ?? [];
    if (multiIds.length > 1 && multiIds.includes(stationId)) {
      draggedStationIds = multiIds;
    } else {
      draggedStationIds = [stationId];
    }

    onHighlight?.(stationId);
    const coords = (feature.geometry as GeoJSON.Point).coordinates as [
      number,
      number,
    ];
    originLngLat = coords;
    startPoint = { x: e.point.x, y: e.point.y };
    dragging = true;
    thresholdMet = false;
    wasDragPanEnabled = map.dragPan.isEnabled();
    if (wasDragPanEnabled) {
      map.dragPan.disable();
    }

    // Don't prevent default click yet — wait for threshold
    e.preventDefault();
  }

  function onMouseMove(e: MapMouseEvent) {
    if (!dragging || !startPoint || !originLngLat) return;

    const dx = e.point.x - startPoint.x;
    const dy = e.point.y - startPoint.y;

    if (!thresholdMet) {
      if (Math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD) return;
      thresholdMet = true;
      map.getCanvas().style.cursor = 'grabbing';
      // Create the DOM ghost so it floats above sidebar/overlays
      domGhost = createDomGhost(draggedStationIds.length);
    }

    // Move the DOM ghost to follow the cursor
    const rect = map.getCanvas().getBoundingClientRect();
    if (domGhost) {
      moveDomGhost(domGhost, rect.left + e.point.x, rect.top + e.point.y);
    }

    // Check if hovering over a driver
    const features = map.queryRenderedFeatures(e.point, {
      layers: [MapLayer.Resources],
    });
    const newHoveredId =
      features && features.length > 0
        ? Number(features[0].properties?.id)
        : null;

    if (newHoveredId !== hoveredDriverId) {
      hoveredDriverId = newHoveredId;
      map.getCanvas().style.cursor =
        hoveredDriverId !== null ? 'copy' : 'grabbing';
    }
  }

  function findResourceIdAtPoint(x: number, y: number): number | null {
    const el = document.elementFromPoint(x, y);
    if (!el) return null;
    const resourceEl = (el as HTMLElement).closest?.('[data-resource-id]');
    if (!resourceEl) return null;
    const id = Number(resourceEl.getAttribute('data-resource-id'));
    return Number.isNaN(id) ? null : id;
  }

  function onWindowMouseMove(e: MouseEvent) {
    if (!dragging || !thresholdMet) return;
    if (domGhost) {
      moveDomGhost(domGhost, e.clientX, e.clientY);
    }
  }

  function onMouseUp(e: MapMouseEvent) {
    if (!dragging) return;

    if (thresholdMet && draggedStationIds.length > 0) {
      // Check for a driver under the cursor
      const features = map.queryRenderedFeatures(e.point, {
        layers: [MapLayer.Resources],
      });

      if (features && features.length > 0) {
        const driverId = Number(features[0].properties?.id);
        if (!Number.isNaN(driverId)) {
          onDrop(draggedStationIds, driverId);
        }
      }
    }

    cleanup();
  }

  // Bind handlers to station layers for mousedown, and globally for move/up
  stationLayers.forEach((layer) => {
    map.on('mousedown', layer, onMouseDown);
  });
  map.on('mousemove', onMouseMove);
  map.on('mouseup', onMouseUp);

  function onWindowMouseUp(e: MouseEvent) {
    if (!dragging) return;
    const target = e.target as Node | null;
    // If released inside the map canvas, let onMouseUp handle it
    if (target && map.getCanvas().contains(target)) return;

    // Check if released over a sidebar resource item
    if (thresholdMet && draggedStationIds.length > 0) {
      const resourceId = findResourceIdAtPoint(e.clientX, e.clientY);
      if (resourceId !== null) {
        onDrop(draggedStationIds, resourceId);
      }
    }

    cleanup();
  }

  window.addEventListener('mouseup', onWindowMouseUp);
  window.addEventListener('mousemove', onWindowMouseMove);

  return () => {
    stationLayers.forEach((layer) => {
      map.off('mousedown', layer, onMouseDown);
    });
    map.off('mousemove', onMouseMove);
    map.off('mouseup', onMouseUp);
    window.removeEventListener('mouseup', onWindowMouseUp);
    window.removeEventListener('mousemove', onWindowMouseMove);
    cleanup();
  };
}
