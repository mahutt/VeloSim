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
import { setupMapClickHandlers } from '~/lib/map-click-handlers';
import type { Map as MapboxMap } from 'mapbox-gl';

test('setupMapClickHandlers registers all event listeners', () => {
  const mockMap = {
    on: vi.fn(),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  expect(mockMap.on).toHaveBeenCalledTimes(7);
  expect(mockMap.on).toHaveBeenCalledWith(
    'click',
    'stations',
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'click',
    'resources',
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith('click', expect.any(Function));
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseenter',
    'stations',
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseleave',
    'stations',
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseenter',
    'resources',
    expect.any(Function)
  );
  expect(mockMap.on).toHaveBeenCalledWith(
    'mouseleave',
    'resources',
    expect.any(Function)
  );
});

test('station click calls onItemSelect with correct data', () => {
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

  const mockEvent = {
    features: [
      {
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: '123', name: 'Test Station' },
      },
    ],
    originalEvent: { stopPropagation: vi.fn() },
  };

  handlers['click-stations'](mockEvent);

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'station',
    id: '123',
    position: [-73.5, 45.5],
    properties: { id: '123', name: 'Test Station' },
  });
  expect(mockEvent.originalEvent.stopPropagation).toHaveBeenCalled();
});

test('station click with no features does nothing', () => {
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

  handlers['click-stations']({ features: [] });

  expect(onItemSelect).not.toHaveBeenCalled();
});

test('station click handles missing properties', () => {
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

  const mockEvent = {
    features: [
      {
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: undefined,
      },
    ],
    originalEvent: { stopPropagation: vi.fn() },
  };

  handlers['click-stations'](mockEvent);

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'station',
    id: 'undefined',
    position: [-73.5, 45.5],
    properties: {},
  });
});

test('resource click calls onItemSelect with correct data', () => {
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

  const mockEvent = {
    features: [
      {
        geometry: { type: 'Point', coordinates: [-73.6, 45.6] },
        properties: { id: 'resource-1' },
      },
    ],
    originalEvent: { stopPropagation: vi.fn() },
  };

  handlers['click-resources'](mockEvent);

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'resource',
    id: 'resource-1',
    position: [-73.6, 45.6],
    properties: { id: 'resource-1' },
  });
  expect(mockEvent.originalEvent.stopPropagation).toHaveBeenCalled();
});

test('resource click with no features does nothing', () => {
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

  handlers['click-resources']({ features: [] });

  expect(onItemSelect).not.toHaveBeenCalled();
});

test('resource click handles missing properties', () => {
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

  const mockEvent = {
    features: [
      {
        geometry: { type: 'Point', coordinates: [-73.6, 45.6] },
        properties: undefined,
      },
    ],
    originalEvent: { stopPropagation: vi.fn() },
  };

  handlers['click-resources'](mockEvent);

  expect(onItemSelect).toHaveBeenCalledWith({
    type: 'resource',
    id: 'undefined',
    position: [-73.6, 45.6],
    properties: {},
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
    { layers: ['stations', 'resources'] }
  );
  expect(onItemSelect).toHaveBeenCalledWith(null);
});

test('clicking map does not deselect if feature exists', () => {
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
    queryRenderedFeatures: vi.fn(() => [{ id: 'some-feature' }]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).not.toHaveBeenCalled();
});

test('mouseenter and mouseleave change cursor', () => {
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
