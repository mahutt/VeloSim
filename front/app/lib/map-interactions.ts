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

// Entities may be represented by more than 1 layer (e.g., stations and their task counts)
// So we use a function to map layers to entity types
function layerToEntityType(layer: MapLayer): SelectedItemType {
  switch (layer) {
    case MapLayer.Stations:
    case MapLayer.StationTaskCounts:
      return SelectedItemType.Station;
    case MapLayer.Resources:
      return SelectedItemType.Resource;
    default:
      throw new Error(`Unrecognized layer: ${layer}`);
  }
}

// Set up click handlers for map layers to enable item selection
type ItemSelectCallback = (
  item: {
    type: SelectedItemType;
    id: number;
    coordinates: [number, number];
  } | null
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
    const features = map.queryRenderedFeatures(e.point, {
      layers: Object.values(MapLayer),
    });

    if (features.length === 0) {
      onItemSelect(null);
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
    const id = Number(feature.properties.id);
    const coordinates = (feature.geometry as GeoJSON.Point).coordinates as [
      number,
      number,
    ];

    onItemSelect({ type, id, coordinates });
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
  requestAssignment: (resourceId: number, taskId: number) => void
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

    const taskId = Number(e.dataTransfer.getData('taskId'));
    if (Number.isNaN(taskId)) return;

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

    requestAssignment(resourceId, taskId);
  };

  canvas.addEventListener('dragover', handleDragOver);
  canvas.addEventListener('drop', handleDrop);

  return () => {
    canvas.removeEventListener('dragover', handleDragOver);
    canvas.removeEventListener('drop', handleDrop);
  };
}
