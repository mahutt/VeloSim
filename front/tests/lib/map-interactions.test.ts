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
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
  setupMapDropHandlers,
} from '~/lib/map-interactions';
import type { Map as MapboxMap } from 'mapbox-gl';
import { MapLayer, MapSource } from '~/lib/map-helpers';
import { SelectedItemType } from '~/types';
// setupMapHoverHandlers imported above

test('setupMapClickHandlers registers event listeners', () => {
  const mockMap = {
    on: vi.fn(),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  // Should register 1 click + 4 cursor listeners (3 layers * 2 events)
  expect(mockMap.on).toHaveBeenCalledTimes(7);
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
    type: SelectedItemType.Station,
    id: 123,
    coordinates: [-73.5, 45.5],
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
        properties: { id: 1, routeId: 1 },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith({
    type: SelectedItemType.Resource,
    id: 1,
    coordinates: [-73.6, 45.6],
  });
});

test('clicking station with missing properties throws error', () => {
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
        layer: { id: MapLayer.Stations },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: undefined,
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  expect(() => {
    handlers['click']({ point: { x: 100, y: 100 } });
  }).toThrow();
});

test('clicking resource with missing properties throws an error', () => {
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

  expect(() => {
    handlers['click']({ point: { x: 100, y: 100 } });
  }).toThrow();
  expect(onItemSelect).not.toHaveBeenCalled();
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
    { layers: Object.values(MapLayer) }
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

test('clicking station task count layer calls onItemSelect with station data', () => {
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
        layer: { id: MapLayer.StationTaskCounts },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 123, name: 'Test Station' },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith({
    type: SelectedItemType.Station,
    id: 123,
    coordinates: [-73.5, 45.5],
  });
});

test('clicking feature with missing layer throws error', () => {
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
        layer: undefined,
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 123 },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  expect(() => {
    handlers['click']({ point: { x: 100, y: 100 } });
  }).toThrow();
});

test('clicking feature with unrecognized layer throws error', () => {
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
        layer: { id: 'unknown-layer' },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 123 },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  expect(() => {
    handlers['click']({ point: { x: 100, y: 100 } });
  }).toThrow();
});

test('mouseenter and mouseleave for station-task-counts layer', () => {
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

  handlers['mouseenter-station-task-counts']();
  expect(canvas.style.cursor).toBe('pointer');

  handlers['mouseleave-station-task-counts']();
  expect(canvas.style.cursor).toBe('');
});

test('registers mousemove and mouseleave handlers for all layers', () => {
  const mockMap = {
    on: vi.fn(),
  } as unknown as MapboxMap;
  const onItemHover = vi.fn();

  setupMapHoverHandlers(mockMap, onItemHover);

  // For each layer: mousemove + mouseleave
  expect(mockMap.on).toHaveBeenCalledTimes(Object.values(MapLayer).length * 2);
  Object.values(MapLayer).forEach((layer) => {
    expect(mockMap.on).toHaveBeenCalledWith(
      'mousemove',
      layer,
      expect.any(Function)
    );
    expect(mockMap.on).toHaveBeenCalledWith(
      'mouseleave',
      layer,
      expect.any(Function)
    );
  });
});

test('calls onItemHover with correct data on mousemove with feature', () => {
  const handlers: Record<
    string,
    (e: { features?: Array<{ properties?: { id?: number } }> }) => void
  > = {};
  const mockMap = {
    on: vi.fn((event, layer, handler) => {
      if (typeof handler === 'function') {
        handlers[`${event}-${layer}`] = handler;
      }
    }),
  } as unknown as MapboxMap;
  const onItemHover = vi.fn();

  setupMapHoverHandlers(mockMap, onItemHover);

  // Simulate mousemove on Stations layer
  handlers[`mousemove-${MapLayer.Stations}`]({
    features: [{ properties: { id: 42 } }],
  });

  expect(onItemHover).toHaveBeenCalledWith({
    type: SelectedItemType.Station,
    id: 42,
  });
});

test('does not call onItemHover if no features on mousemove', () => {
  const handlers: Record<
    string,
    (e: { features?: Array<{ properties?: { id?: number } }> }) => void
  > = {};
  const mockMap = {
    on: vi.fn((event, layer, handler) => {
      if (typeof handler === 'function') {
        handlers[`${event}-${layer}`] = handler;
      }
    }),
  } as unknown as MapboxMap;
  const onItemHover = vi.fn();

  setupMapHoverHandlers(mockMap, onItemHover);

  handlers[`mousemove-${MapLayer.Resources}`]({ features: [] });
  expect(onItemHover).not.toHaveBeenCalled();
});

test('does not call onItemHover if feature has no id', () => {
  const handlers: Record<
    string,
    (e: { features?: Array<{ properties?: { id?: number } }> }) => void
  > = {};
  const mockMap = {
    on: vi.fn((event, layer, handler) => {
      if (typeof handler === 'function') {
        handlers[`${event}-${layer}`] = handler;
      }
    }),
  } as unknown as MapboxMap;
  const onItemHover = vi.fn();

  setupMapHoverHandlers(mockMap, onItemHover);

  handlers[`mousemove-${MapLayer.Resources}`]({
    features: [{ properties: {} }],
  });
  expect(onItemHover).not.toHaveBeenCalled();
});

test('calls onItemHover(null) on mouseleave', () => {
  const handlers: Record<string, () => void> = {};
  const mockMap = {
    on: vi.fn((event, layer, handler) => {
      if (typeof handler === 'function') {
        handlers[`${event}-${layer}`] = handler;
      }
    }),
  } as unknown as MapboxMap;
  const onItemHover = vi.fn();

  setupMapHoverHandlers(mockMap, onItemHover);

  handlers[`mouseleave-${MapLayer.Stations}`]();
  expect(onItemHover).toHaveBeenCalledWith(null);
});

test('drop assigns task to resource when dropped on resource and cleanup removes listeners', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(() => {}),
    getBoundingClientRect: vi.fn(() => ({ left: 10, top: 20 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => [
      {
        properties: { id: 7 },
        geometry: { type: 'Point', coordinates: [-73.6, 45.6] },
      },
    ]),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();

  const cleanup = setupMapDropHandlers(mockMap, requestAssignment);

  expect(canvas.addEventListener).toHaveBeenCalledWith(
    'dragover',
    expect.any(Function)
  );
  expect(canvas.addEventListener).toHaveBeenCalledWith(
    'drop',
    expect.any(Function)
  );

  // simulate dragover
  const dragOverPrevent = vi.fn();
  const dragOverEvent = {
    preventDefault: dragOverPrevent,
    dataTransfer: { dropEffect: '' },
  } as unknown as DragEvent;
  listeners['dragover'](dragOverEvent);
  expect(dragOverPrevent).toHaveBeenCalled();
  expect(dragOverEvent.dataTransfer!.dropEffect).toBe('move');

  // simulate drop with valid taskId
  const dropPrevent = vi.fn();
  const dropGetData = vi.fn(() => '99');
  const dropEvent = {
    preventDefault: dropPrevent,
    dataTransfer: { getData: dropGetData },
    clientX: 15,
    clientY: 25,
  } as unknown as DragEvent;

  listeners['drop'](dropEvent);

  expect(dropPrevent).toHaveBeenCalled();
  expect(mockMap.queryRenderedFeatures).toHaveBeenCalledWith([5, 5], {
    layers: [MapLayer.Resources],
  });
  expect(requestAssignment).toHaveBeenCalledWith(7, 99);

  cleanup();
  expect(canvas.removeEventListener).toHaveBeenCalledWith(
    'dragover',
    expect.any(Function)
  );
  expect(canvas.removeEventListener).toHaveBeenCalledWith(
    'drop',
    expect.any(Function)
  );
});

test('drop ignores invalid taskId and missing features', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(() => {}),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  const cleanup = setupMapDropHandlers(mockMap, requestAssignment);

  const dropInvalidPrevent = vi.fn();
  const dropEventInvalid = {
    preventDefault: dropInvalidPrevent,
    dataTransfer: { getData: vi.fn(() => 'not-a-number') },
    clientX: 10,
    clientY: 10,
  } as unknown as DragEvent;

  listeners['drop'](dropEventInvalid);
  expect(dropInvalidPrevent).toHaveBeenCalled();
  expect(requestAssignment).not.toHaveBeenCalled();

  const dropNoFeaturesPrevent = vi.fn();
  const dropEventNoFeatures = {
    preventDefault: dropNoFeaturesPrevent,
    dataTransfer: { getData: vi.fn(() => '42') },
    clientX: 10,
    clientY: 10,
  } as unknown as DragEvent;

  listeners['drop'](dropEventNoFeatures);
  expect(requestAssignment).not.toHaveBeenCalled();

  cleanup();
});
