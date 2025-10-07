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

import { expect, test, vi } from 'vitest';
import { setupMapClickHandlers } from '~/lib/map-interactions';
import type { Map as MapboxMap } from 'mapbox-gl';
import { MapSource } from '~/lib/map-helpers';

test('setupMapClickHandlers registers event listeners', () => {
  const mockMap = {
    on: vi.fn(),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  // Should register 1 click + 4 cursor listeners (2 layers * 2 events)
  expect(mockMap.on).toHaveBeenCalledTimes(5);
  expect(mockMap.on).toHaveBeenCalledWith('click', expect.any(Function));
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseenter',
    MapSource.Stations,
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseleave',
    MapSource.Stations,
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseenter',
    MapSource.Resources,
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseleave',
    MapSource.Resources,
    expect.any(Function)
  );
});

test('clicking station calls onItemSelect with wrapped station data', () => {
  const handlers: Record<string, (event: unknown) => void> = {};
  const mockMap = {
    on: vi.fn(
      (
        event: string,
        layerOrHandler: string | ((e: unknown) => void),
        handler?: (e: unknown) => void
      ) => {
        if (typeof layerOrHandler === 'function') {
          handlers[event] = layerOrHandler;
        } else if (handler) {
          handlers[`${event}-${layerOrHandler}`] = handler;
        }
      }
    ),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => [
      {
        layer: { id: MapSource.Stations },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 123, name: 'Test Station' },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'station',
    value: {
      id: 123,
      name: 'Test Station',
      position: [-73.5, 45.5],
    },
  });
});

test('clicking resource calls onItemSelect with wrapped resource data', () => {
  const handlers: Record<string, (event: unknown) => void> = {};
  const mockMap = {
    on: vi.fn(
      (
        event: string,
        layerOrHandler: string | ((e: unknown) => void),
        handler?: (e: unknown) => void
      ) => {
        if (typeof layerOrHandler === 'function') {
          handlers[event] = layerOrHandler;
        } else if (handler) {
          handlers[`${event}-${layerOrHandler}`] = handler;
        }
      }
    ),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => [
      {
        layer: { id: MapSource.Resources },
        geometry: { type: 'Point', coordinates: [-73.6, 45.6] },
        properties: { id: 'resource-1', routeId: 'route-1' },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'resource',
    value: {
      id: 'resource-1',
      position: [-73.6, 45.6],
      routeId: 'route-1',
    },
  });
});

test('clicking station with missing properties uses defaults', () => {
  const handlers: Record<string, (event: unknown) => void> = {};
  const mockMap = {
    on: vi.fn(
      (
        event: string,
        layerOrHandler: string | ((e: unknown) => void),
        handler?: (e: unknown) => void
      ) => {
        if (typeof layerOrHandler === 'function') {
          handlers[event] = layerOrHandler;
        } else if (handler) {
          handlers[`${event}-${layerOrHandler}`] = handler;
        }
      }
    ),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => [
      {
        layer: { id: MapSource.Stations },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: undefined,
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'station',
    value: {
      id: NaN,
      name: '',
      position: [-73.5, 45.5],
    },
  });
});

test('clicking resource with missing properties uses defaults', () => {
  const handlers: Record<string, (event: unknown) => void> = {};
  const mockMap = {
    on: vi.fn(
      (
        event: string,
        layerOrHandler: string | ((e: unknown) => void),
        handler?: (e: unknown) => void
      ) => {
        if (typeof layerOrHandler === 'function') {
          handlers[event] = layerOrHandler;
        } else if (handler) {
          handlers[`${event}-${layerOrHandler}`] = handler;
        }
      }
    ),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => [
      {
        layer: { id: MapSource.Resources },
        geometry: { type: 'Point', coordinates: [-73.6, 45.6] },
        properties: undefined,
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'resource',
    value: {
      id: 'undefined',
      position: [-73.6, 45.6],
      routeId: '',
    },
  });
});

test('clicking empty map area deselects item', () => {
  const handlers: Record<string, (event: unknown) => void> = {};
  const mockMap = {
    on: vi.fn(
      (
        event: string,
        layerOrHandler: string | ((e: unknown) => void),
        handler?: (e: unknown) => void
      ) => {
        if (typeof layerOrHandler === 'function') {
          handlers[event] = layerOrHandler;
        } else if (handler) {
          handlers[`${event}-${layerOrHandler}`] = handler;
        }
      }
    ),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(mockMap.queryRenderedFeatures).toHaveBeenCalledWith(
    { x: 100, y: 100 },
    { layers: [MapSource.Stations, MapSource.Resources] }
  );
  expect(onItemSelect).toHaveBeenCalledWith(null);
});

test('mouseenter and mouseleave change cursor for all layers', () => {
  const handlers: Record<string, () => void> = {};
  const canvas = { style: { cursor: '' } };
  const mockMap = {
    on: vi.fn(
      (
        event: string,
        layerOrHandler: string | (() => void),
        handler?: () => void
      ) => {
        if (typeof layerOrHandler === 'function') {
          handlers[event] = layerOrHandler;
        } else if (handler) {
          handlers[`${event}-${layerOrHandler}`] = handler;
        }
      }
    ),
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['mouseenter-stations']();
  expect(canvas.style.cursor).toBe('pointer');

  handlers['mouseleave-stations']();
  expect(canvas.style.cursor).toBe('');

  handlers['mouseenter-resources']();
  expect(canvas.style.cursor).toBe('pointer');

  handlers['mouseleave-resources']();
  expect(canvas.style.cursor).toBe('');
});
