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
import type { Station, Resource, SelectedItem } from '~/types';
import { MapSource } from './map-helpers';

//Set up click handlers for map layers to enable item selection

export function setupMapClickHandlers(
  map: MapboxMap,
  onItemSelect: (item: SelectedItem | null) => void
) {
  map.on('click', (e: MapMouseEvent) => {
    const interactiveLayers = [MapSource.Stations, MapSource.Resources];

    const features = map.queryRenderedFeatures(e.point, {
      layers: interactiveLayers,
    });

    if (features.length === 0) {
      onItemSelect(null);
      //TODO: Remove when UI is implemented
      console.log('No item clicked');
      return;
    }

    const feature = features[0];
    const coordinates = (feature.geometry as GeoJSON.Point).coordinates as [
      number,
      number,
    ];

    // Determine if the clicked feature is a station or resource and call onItemSelect accordingly
    if (feature.layer && feature.layer.id === MapSource.Stations) {
      const station: Station = {
        id: Number(feature.properties?.id),
        name: feature.properties?.name || '',
        position: coordinates,
      };
      onItemSelect({ type: 'station', value: station });
      //TODO: Remove when UI is implemented
      console.log('Station clicked:', station);
    } else if (feature.layer && feature.layer.id === MapSource.Resources) {
      const resource: Resource = {
        id: String(feature.properties?.id),
        position: coordinates,
        routeId: feature.properties?.routeId || '',
      };
      onItemSelect({ type: 'resource', value: resource });
      //TODO: Remove when UI is implemented
      console.log('Resource clicked:', resource);
    }
  });

  const interactiveLayers = [MapSource.Stations, MapSource.Resources];

  interactiveLayers.forEach((layer) => {
    map.on('mouseenter', layer, () => {
      map.getCanvas().style.cursor = 'pointer';
    });

    map.on('mouseleave', layer, () => {
      map.getCanvas().style.cursor = '';
    });
  });
}
