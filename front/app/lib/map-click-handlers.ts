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
import type { SelectedItem } from '~/types';

/**
 * Set up click handlers for map layers to enable item selection
 */
export function setupMapClickHandlers(
  map: MapboxMap,
  onItemSelect: (item: SelectedItem | null) => void
) {
  // Handle station clicks
  map.on('click', 'stations', (e: MapMouseEvent) => {
    if (!e.features || e.features.length === 0) return;

    const feature = e.features[0];
    const coordinates = (feature.geometry as GeoJSON.Point).coordinates as [
      number,
      number,
    ];

    onItemSelect({
      type: 'station',
      id: String(feature.properties?.id),
      position: coordinates,
      properties: feature.properties || {},
    });

    //TODO: Remove after implementing selection UI
    console.log('Station clicked:', feature.properties);

    e.originalEvent.stopPropagation();
  });

  // Handle resource clicks
  map.on('click', 'resources', (e: MapMouseEvent) => {
    if (!e.features || e.features.length === 0) return;

    const feature = e.features[0];
    const coordinates = (feature.geometry as GeoJSON.Point).coordinates as [
      number,
      number,
    ];

    onItemSelect({
      type: 'resource',
      id: String(feature.properties?.id),
      position: coordinates,
      properties: feature.properties || {},
    });

    //TODO: Remove after implementing selection UI
    console.log('Resource clicked:', feature.properties);

    e.originalEvent.stopPropagation();
  });

  // Deselect when clicking empty map area
  map.on('click', (e: MapMouseEvent) => {
    // Check if click was on a layer feature
    const features = map.queryRenderedFeatures(e.point, {
      layers: ['stations', 'resources'],
    });

    // Only deselect if clicking empty space
    if (features.length === 0) {
      onItemSelect(null);

      //TODO: Remove after implementing selection UI
      console.log('Deselection click, features found:', features.length);
    }
  });

  // Cursor changes on hover
  map.on('mouseenter', 'stations', () => {
    map.getCanvas().style.cursor = 'pointer';
  });

  map.on('mouseleave', 'stations', () => {
    map.getCanvas().style.cursor = '';
  });

  map.on('mouseenter', 'resources', () => {
    map.getCanvas().style.cursor = 'pointer';
  });

  map.on('mouseleave', 'resources', () => {
    map.getCanvas().style.cursor = '';
  });
}
