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

import { afterEach, describe, expect, test, vi } from 'vitest';
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
  setupMapDropHandlers,
  setupStationDragHandlers,
  setupBoxSelectHandlers,
} from '~/lib/map-interactions';
import type { StationDragDropCallback } from '~/lib/map-interactions';
import type { Map as MapboxMap } from 'mapbox-gl';
import { MapLayer, MapSource } from '~/lib/map-helpers';
import { SelectedItemType } from '~/components/map/selected-item-bar';
// setupMapHoverHandlers imported above

test('setupMapClickHandlers registers event listeners', () => {
  const mockMap = {
    on: vi.fn(),
    getCanvas: vi.fn(() => ({ style: { cursor: '' } })),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  // Should register 1 click + 2 cursor listeners per map layer
  expect(mockMap.on).toHaveBeenCalledTimes(
    1 + Object.values(MapLayer).length * 2
  );
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

  expect(onItemSelect).toHaveBeenCalledWith(
    {
      type: SelectedItemType.Station,
      id: 123,
      coordinates: [-73.5, 45.5],
    },
    { ctrlKey: false }
  );
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

  expect(onItemSelect).toHaveBeenCalledWith(
    {
      type: SelectedItemType.Driver,
      id: 1,
      coordinates: [-73.6, 45.6],
    },
    { ctrlKey: false }
  );
});

test('clicking station with missing properties throws', () => {
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
  }).toThrow('Clicked feature has no id property');
});

test('clicking resource with missing properties throws', () => {
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
  }).toThrow('Clicked feature has no id property');
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
  expect(onItemSelect).toHaveBeenCalledWith(null, { ctrlKey: false });
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

  expect(onItemSelect).toHaveBeenCalledWith(
    {
      type: SelectedItemType.Station,
      id: 123,
      coordinates: [-73.5, 45.5],
    },
    { ctrlKey: false }
  );
});

test('clicking feature with missing layer throws', () => {
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
  }).toThrow('Clicked feature is not from a recognized layer');
});

test('clicking feature with unrecognized layer throws', () => {
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
  }).toThrow('Clicked feature is not from a recognized layer');
});

test('clicking station-circle layer selects the station', () => {
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
        layer: { id: MapLayer.StationCircle },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 123 },
      },
    ]),
  } as unknown as MapboxMap;

  const onItemSelect = vi.fn();
  setupMapClickHandlers(mockMap, onItemSelect);

  handlers['click']({ point: { x: 100, y: 100 } });

  expect(onItemSelect).toHaveBeenCalledWith(
    {
      type: SelectedItemType.Station,
      id: 123,
      coordinates: [-73.5, 45.5],
    },
    { ctrlKey: false }
  );
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

test('hover mousemove on station-circle layer returns station hover data', () => {
  const handlers: Record<
    string,
    (e: { features?: Array<{ properties?: { id?: number } }> }) => void
  > = {};
  const mockMap = {
    on: vi.fn((event: string, layer: string, handler: (e: unknown) => void) => {
      if (typeof handler === 'function') {
        handlers[`${event}-${layer}`] = handler;
      }
    }),
  } as unknown as MapboxMap;
  const onItemHover = vi.fn();

  setupMapHoverHandlers(mockMap, onItemHover);

  handlers[`mousemove-${MapLayer.StationCircle}`]({
    features: [{ properties: { id: 42 } }],
  });

  expect(onItemHover).toHaveBeenCalledWith({
    type: SelectedItemType.Station,
    id: 42,
  });
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

test('drop with no dataTransfer is ignored', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  setupMapDropHandlers(mockMap, requestAssignment);

  // drop with no dataTransfer at all
  listeners['drop']({ preventDefault: vi.fn(), dataTransfer: null });
  expect(requestAssignment).not.toHaveBeenCalled();
});

test('drop with invalid JSON taskIds payload returns early', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  setupMapDropHandlers(mockMap, requestAssignment);

  // dataTransfer.getData returns invalid JSON
  listeners['drop']({
    preventDefault: vi.fn(),
    dataTransfer: { getData: vi.fn(() => '{not-valid-json}') },
    clientX: 10,
    clientY: 10,
  });
  expect(requestAssignment).not.toHaveBeenCalled();
});

test('drop with empty taskIds array returns early', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  setupMapDropHandlers(mockMap, requestAssignment);

  // dataTransfer returns a valid JSON empty array
  listeners['drop']({
    preventDefault: vi.fn(),
    dataTransfer: { getData: vi.fn(() => '[]') },
    clientX: 10,
    clientY: 10,
  });
  expect(requestAssignment).not.toHaveBeenCalled();
});

test('drop with no taskIds key returns early (empty payload)', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => []),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  setupMapDropHandlers(mockMap, requestAssignment);

  // dataTransfer.getData returns empty string (no taskIds key set)
  listeners['drop']({
    preventDefault: vi.fn(),
    dataTransfer: { getData: vi.fn(() => '') },
    clientX: 10,
    clientY: 10,
  });
  expect(requestAssignment).not.toHaveBeenCalled();
});

test('drop on resource with NaN id is ignored', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
    queryRenderedFeatures: vi.fn(() => [
      {
        properties: { id: undefined },
        geometry: { type: 'Point', coordinates: [-73.6, 45.6] },
      },
    ]),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  setupMapDropHandlers(mockMap, requestAssignment);

  listeners['drop']({
    preventDefault: vi.fn(),
    dataTransfer: { getData: vi.fn(() => '[1, 2, 3]') },
    clientX: 10,
    clientY: 10,
  });
  expect(requestAssignment).not.toHaveBeenCalled();
});

test('dragover without dataTransfer does not throw', () => {
  const listeners: Record<string, (e: unknown) => void> = {};
  const canvas = {
    addEventListener: vi.fn((event: string, handler: (e: unknown) => void) => {
      listeners[event] = handler;
    }),
    removeEventListener: vi.fn(),
    getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
  } as unknown as HTMLCanvasElement;

  const mockMap = {
    getCanvas: vi.fn(() => canvas),
  } as unknown as MapboxMap;

  const requestAssignment = vi.fn();
  setupMapDropHandlers(mockMap, requestAssignment);

  const preventDefault = vi.fn();
  // dragover with null dataTransfer
  listeners['dragover']({ preventDefault, dataTransfer: null });
  expect(preventDefault).toHaveBeenCalled();
});

// ---------------------------------------------------------------------------
// setupStationDragHandlers
// ---------------------------------------------------------------------------

describe('setupStationDragHandlers', () => {
  // Helper: create a mock map with handler capture
  function createMockMap() {
    const mapHandlers: Record<string, (e: unknown) => void> = {};
    const canvas = {
      style: { cursor: '' },
      getBoundingClientRect: vi.fn(() => ({ left: 0, top: 0 })),
      contains: vi.fn(() => true),
    };

    const mockMap = {
      on: vi.fn(
        (
          event: string,
          layerOrHandler: string | ((e: unknown) => void),
          handler?: (e: unknown) => void
        ) => {
          if (typeof layerOrHandler === 'function') {
            mapHandlers[event] = layerOrHandler;
          } else if (handler) {
            mapHandlers[`${event}-${layerOrHandler}`] = handler;
          }
        }
      ),
      off: vi.fn(),
      getCanvas: vi.fn(() => canvas),
      getSource: vi.fn(() => undefined),
      queryRenderedFeatures: vi.fn(() => []),
      dragPan: {
        isEnabled: vi.fn(() => true),
        enable: vi.fn(),
        disable: vi.fn(),
      },
      unproject: vi.fn((point: [number, number]) => ({
        lng: -73.5 + point[0] * 0.001,
        lat: 45.5 + point[1] * 0.001,
      })),
    } as unknown as MapboxMap;

    return { mockMap, mapHandlers, canvas };
  }

  // Helper: simulate a mousedown on a station feature
  function stationFeature(
    id: number,
    coords: [number, number] = [-73.5, 45.5]
  ) {
    return {
      properties: { id },
      geometry: { type: 'Point', coordinates: coords },
    };
  }

  // Capture window event listeners so we can invoke & clean them up
  let windowListeners: Record<string, EventListener> = {};
  const origAddEventListener = window.addEventListener;
  const origRemoveEventListener = window.removeEventListener;

  afterEach(() => {
    // Restore originals
    window.addEventListener = origAddEventListener;
    window.removeEventListener = origRemoveEventListener;
    windowListeners = {};
    // Clean up any leftover DOM ghosts from station drag tests
    document
      .querySelectorAll('[data-testid="station-drag-ghost"]')
      .forEach((el) => el.remove());
  });

  function interceptWindowListeners() {
    windowListeners = {};
    window.addEventListener = vi.fn(
      (event: string, handler: EventListenerOrEventListenerObject) => {
        windowListeners[event] = handler as EventListener;
      }
    ) as unknown as typeof window.addEventListener;
    window.removeEventListener =
      vi.fn() as unknown as typeof window.removeEventListener;
  }

  function initDragHandlers(
    map: MapboxMap,
    onDrop: StationDragDropCallback,
    onHighlight = vi.fn(),
    getMultiSelectedStationIds = vi.fn(() => [] as number[]),
    onDragStart = vi.fn(),
    getTaskCountForStation = vi.fn(() => 0)
  ) {
    return setupStationDragHandlers(
      map,
      onDrop,
      onHighlight,
      getMultiSelectedStationIds,
      onDragStart,
      getTaskCountForStation
    );
  }

  test('registers mousedown on station layers, mousemove, mouseup, and window listeners', () => {
    interceptWindowListeners();
    const { mockMap } = createMockMap();
    const onDrop = vi.fn();

    initDragHandlers(mockMap, onDrop);

    // mousedown on Stations + StationCircle + StationRing + StationTaskCounts
    expect(mockMap.on).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.Stations,
      expect.any(Function)
    );
    expect(mockMap.on).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.StationCircle,
      expect.any(Function)
    );
    expect(mockMap.on).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.StationRing,
      expect.any(Function)
    );
    expect(mockMap.on).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.StationTaskCounts,
      expect.any(Function)
    );
    // global map mousemove + mouseup = 2 calls
    expect(mockMap.on).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(mockMap.on).toHaveBeenCalledWith('mouseup', expect.any(Function));

    // window listeners
    expect(window.addEventListener).toHaveBeenCalledWith(
      'mouseup',
      expect.any(Function)
    );
    expect(window.addEventListener).toHaveBeenCalledWith(
      'mousemove',
      expect.any(Function)
    );
  });

  test('cleanup removes all map and window listeners', () => {
    interceptWindowListeners();
    const { mockMap } = createMockMap();
    const onDrop = vi.fn();

    const cleanup = initDragHandlers(mockMap, onDrop);
    cleanup();

    expect(mockMap.off).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.Stations,
      expect.any(Function)
    );
    expect(mockMap.off).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.StationCircle,
      expect.any(Function)
    );
    expect(mockMap.off).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.StationRing,
      expect.any(Function)
    );
    expect(mockMap.off).toHaveBeenCalledWith(
      'mousedown',
      MapLayer.StationTaskCounts,
      expect.any(Function)
    );
    expect(mockMap.off).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(mockMap.off).toHaveBeenCalledWith('mouseup', expect.any(Function));
    expect(window.removeEventListener).toHaveBeenCalledWith(
      'mouseup',
      expect.any(Function)
    );
    expect(window.removeEventListener).toHaveBeenCalledWith(
      'mousemove',
      expect.any(Function)
    );
  });

  test('mousedown on station only highlights; dragPan is disabled after threshold', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(42)]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    const mouseDownEvent = {
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    };

    mapHandlers[`mousedown-${MapLayer.Stations}`](mouseDownEvent);

    expect(onHighlight).toHaveBeenCalledWith(42);
    expect(mockMap.dragPan.isEnabled).not.toHaveBeenCalled();
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();

    // Exceed threshold to start station drag mode
    (mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>).mockReturnValue(
      []
    );
    mapHandlers['mousemove']({ point: { x: 106, y: 100 } });

    expect(mockMap.dragPan.isEnabled).toHaveBeenCalled();
    expect(mockMap.dragPan.disable).toHaveBeenCalled();
  });

  test('mousedown is ignored when no features are found', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    const mouseDownEvent = {
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    };

    mapHandlers[`mousedown-${MapLayer.Stations}`](mouseDownEvent);

    expect(onHighlight).not.toHaveBeenCalled();
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();
  });

  test('drag below threshold does not activate dragging visuals', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(1)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // mousemove only 2px — below threshold of 5
    mapHandlers['mousemove']({
      point: { x: 102, y: 100 },
    });

    expect(canvas.style.cursor).toBe('');
    expect(
      document.querySelector('[data-testid="station-drag-ghost"]')
    ).toBeNull();
  });

  test('drag above threshold activates cursor and ghost via window mousemove', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();

    (mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>).mockReturnValue(
      [stationFeature(1)]
    );

    initDragHandlers(mockMap, onDrop);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // map mousemove exceeding threshold (6px)
    (mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>).mockReturnValue(
      []
    );
    mapHandlers['mousemove']({
      point: { x: 106, y: 100 },
    });

    expect(canvas.style.cursor).toBe('grabbing');

    // window mousemove should update DOM ghost position
    windowListeners['mousemove']({ clientX: 200, clientY: 300 } as MouseEvent);

    const ghost = document.querySelector(
      '[data-testid="station-drag-ghost"]'
    ) as HTMLElement;
    expect(ghost).not.toBeNull();
    expect(ghost.style.left).toBe('200px');
    expect(ghost.style.top).toBe('300px');
  });

  test('cursor changes to copy when hovering over a driver during drag', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(1)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // exceed threshold with no driver
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 106, y: 100 } });
    expect(canvas.style.cursor).toBe('grabbing');

    // move over a driver
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([{ properties: { id: 7 } }]);
    mapHandlers['mousemove']({ point: { x: 110, y: 100 } });
    expect(canvas.style.cursor).toBe('copy');

    // move away from driver
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 115, y: 100 } });
    expect(canvas.style.cursor).toBe('grabbing');
  });

  test('mouseup on a driver triggers onDrop', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(10)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown on station 10
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // exceed threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 106, y: 100 } });

    // mouseup on driver 5
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([{ properties: { id: 5 } }]);
    mapHandlers['mouseup']({ point: { x: 110, y: 100 } });

    expect(onDrop).toHaveBeenCalledWith([10], 5);
  });

  test('mouseup without exceeding threshold does not call onDrop', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(10)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // mouseup without mousemove
    mapHandlers['mouseup']({ point: { x: 101, y: 100 } });

    expect(onDrop).not.toHaveBeenCalled();
  });

  test('mouseup on empty area (no driver) does not call onDrop', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(10)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // exceed threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 106, y: 100 } });

    // mouseup on empty space
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mouseup']({ point: { x: 120, y: 100 } });

    expect(onDrop).not.toHaveBeenCalled();
  });

  test('cleanup restores dragPan and calls onHighlight(null)', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(7)]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    // mousedown starts station interaction
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // exceed threshold so station drag mode is entered and dragPan is disabled
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });

    expect(mockMap.dragPan.disable).toHaveBeenCalled();
    onHighlight.mockClear();

    // mouseup triggers cleanup
    mapHandlers['mouseup']({ point: { x: 101, y: 100 } });

    // dragPan should be re-enabled (it was enabled before)
    expect(mockMap.dragPan.enable).toHaveBeenCalled();
    // onHighlight(null) called during cleanup
    expect(onHighlight).toHaveBeenCalledWith(null);
    // DOM ghost removed
    expect(
      document.querySelector('[data-testid="station-drag-ghost"]')
    ).toBeNull();
    // cursor reset
    expect(canvas.style.cursor).toBe('');
  });

  test('dragPan stays disabled if it was disabled before drag', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();

    // dragPan was already disabled
    (mockMap.dragPan.isEnabled as ReturnType<typeof vi.fn>).mockReturnValue(
      false
    );

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(1)]);

    initDragHandlers(mockMap, onDrop);

    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // Not yet in drag mode (threshold not crossed), so disable should not be called
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();

    // Exceed threshold to enter station drag mode
    (mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>).mockReturnValue(
      []
    );
    mapHandlers['mousemove']({ point: { x: 106, y: 100 } });

    // Since it was already disabled, disable should still NOT be called
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();

    // mouseup → cleanup
    mapHandlers['mouseup']({ point: { x: 101, y: 100 } });

    // dragPan should stay disabled (enable should NOT be called)
    expect(mockMap.dragPan.enable).not.toHaveBeenCalled();
  });

  test('window mouseup outside canvas cancels drag', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(5)]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    onHighlight.mockClear();

    // Simulate window mouseup outside the canvas
    (canvas.contains as ReturnType<typeof vi.fn>).mockReturnValue(false);
    windowListeners['mouseup']({
      target: document.body,
    } as unknown as MouseEvent);

    // Should cancel: onHighlight(null), DOM ghost removed, dragPan restored
    expect(onHighlight).toHaveBeenCalledWith(null);
    expect(
      document.querySelector('[data-testid="station-drag-ghost"]')
    ).toBeNull();
    expect(onDrop).not.toHaveBeenCalled();
  });

  test('window mouseup inside canvas does not cancel drag', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(5)]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    onHighlight.mockClear();

    // Simulate window mouseup inside the canvas
    (canvas.contains as ReturnType<typeof vi.fn>).mockReturnValue(true);
    windowListeners['mouseup']({ target: canvas } as unknown as MouseEvent);

    // Should NOT cancel — the map's own mouseup handler handles this
    expect(onHighlight).not.toHaveBeenCalledWith(null);
  });

  test('window mousemove does not update ghost before threshold is met', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(1)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // window mousemove without exceeding threshold
    windowListeners['mousemove']({ clientX: 102, clientY: 100 } as MouseEvent);

    expect(
      document.querySelector('[data-testid="station-drag-ghost"]')
    ).toBeNull();
  });

  test('mousedown is ignored when feature has no id', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([
      {
        properties: {},
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
      },
    ]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    expect(onHighlight).not.toHaveBeenCalled();
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();
  });

  test('mousemove when not dragging is a no-op', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();

    initDragHandlers(mockMap, onDrop);

    // mousemove without prior mousedown
    mapHandlers['mousemove']({ point: { x: 100, y: 100 } });

    expect(canvas.style.cursor).toBe('');
    expect(mockMap.queryRenderedFeatures).not.toHaveBeenCalled();
  });

  test('window mousemove when not dragging is a no-op', () => {
    interceptWindowListeners();
    const { mockMap } = createMockMap();
    const onDrop = vi.fn();

    initDragHandlers(mockMap, onDrop);

    // window mousemove without prior mousedown
    windowListeners['mousemove']({ clientX: 200, clientY: 300 } as MouseEvent);

    expect(
      document.querySelector('[data-testid="station-drag-ghost"]')
    ).toBeNull();
  });

  test('window mouseup when not dragging is a no-op', () => {
    interceptWindowListeners();
    const { mockMap } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    initDragHandlers(mockMap, onDrop, onHighlight);

    // window mouseup without prior mousedown
    windowListeners['mouseup']({
      target: document.body,
    } as unknown as MouseEvent);

    expect(onHighlight).not.toHaveBeenCalled();
    expect(onDrop).not.toHaveBeenCalled();
  });

  test('window mouseup over sidebar resource item triggers onDrop', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(10)]);

    initDragHandlers(mockMap, onDrop);

    // mousedown on station
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    // exceed threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });
    expect(canvas.style.cursor).toBe('grabbing');

    // Simulate a sidebar resource element under the cursor
    const div = document.createElement('div');
    div.setAttribute('data-resource-id', '77');
    document.body.appendChild(div);
    vi.spyOn(document, 'elementFromPoint').mockReturnValueOnce(div);

    // Release outside canvas → should find resource via DOM
    (canvas.contains as ReturnType<typeof vi.fn>).mockReturnValueOnce(false);
    windowListeners['mouseup']({
      target: div,
      clientX: 500,
      clientY: 300,
    } as unknown as MouseEvent);

    expect(onDrop).toHaveBeenCalledWith([10], 77);

    // cleanup
    div.remove();
    vi.restoreAllMocks();
  });

  test('window mouseup over sidebar with NaN resource id does not call onDrop', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(10)]);

    initDragHandlers(mockMap, onDrop);

    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });

    // Resource element with non-numeric id
    const div = document.createElement('div');
    div.setAttribute('data-resource-id', 'abc');
    document.body.appendChild(div);
    vi.spyOn(document, 'elementFromPoint').mockReturnValueOnce(div);

    (canvas.contains as ReturnType<typeof vi.fn>).mockReturnValueOnce(false);
    windowListeners['mouseup']({
      target: div,
      clientX: 500,
      clientY: 300,
    } as unknown as MouseEvent);

    expect(onDrop).not.toHaveBeenCalled();

    div.remove();
    vi.restoreAllMocks();
  });

  test('full drag flow: mousedown → exceed threshold → drop on driver → cleanup', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers, canvas } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    initDragHandlers(mockMap, onDrop, onHighlight);

    // 1. mousedown on station 42
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(42, [-73.55, 45.52])]);
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      preventDefault: vi.fn(),
    });
    expect(onHighlight).toHaveBeenCalledWith(42);

    // 2. mousemove exceeds threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });
    expect(mockMap.dragPan.disable).toHaveBeenCalled();
    expect(canvas.style.cursor).toBe('grabbing');

    // 3. window mousemove updates DOM ghost
    windowListeners['mousemove']({ clientX: 150, clientY: 200 } as MouseEvent);
    const ghost = document.querySelector(
      '[data-testid="station-drag-ghost"]'
    ) as HTMLElement;
    expect(ghost).not.toBeNull();
    expect(ghost.style.left).toBe('150px');
    expect(ghost.style.top).toBe('200px');

    // 4. hover over driver 99 → cursor changes
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([{ properties: { id: 99 } }]);
    mapHandlers['mousemove']({ point: { x: 120, y: 100 } });
    expect(canvas.style.cursor).toBe('copy');

    // 5. mouseup on driver 99 → onDrop called
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([{ properties: { id: 99 } }]);
    mapHandlers['mouseup']({ point: { x: 120, y: 100 } });
    expect(onDrop).toHaveBeenCalledWith([42], 99);

    // 6. cleanup effects
    expect(onHighlight).toHaveBeenCalledWith(null);
    expect(mockMap.dragPan.enable).toHaveBeenCalled();
    expect(canvas.style.cursor).toBe('');
  });

  test('multi-station drag: drags all multi-selected stations when clicking a selected one', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const getMultiSelectedStationIds = vi.fn(() => [10, 20, 30]);

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(20)]);

    initDragHandlers(mockMap, onDrop, undefined, getMultiSelectedStationIds);

    // mousedown on station 20 (which is part of multi-selection)
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      originalEvent: { shiftKey: false },
      preventDefault: vi.fn(),
    });

    // exceed threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });

    // mouseup on driver 5
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([{ properties: { id: 5 } }]);
    mapHandlers['mouseup']({ point: { x: 120, y: 100 } });

    // Should drop all multi-selected stations, not just station 20
    expect(onDrop).toHaveBeenCalledWith([10, 20, 30], 5);
  });

  test('multi-station drag: drags single station when it is not in multi-selection', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const getMultiSelectedStationIds = vi.fn(() => [10, 20]);

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(99)]);

    initDragHandlers(mockMap, onDrop, undefined, getMultiSelectedStationIds);

    // mousedown on station 99 (NOT in multi-selection)
    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      originalEvent: { shiftKey: false },
      preventDefault: vi.fn(),
    });

    // exceed threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });

    // mouseup on driver 5
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([{ properties: { id: 5 } }]);
    mapHandlers['mouseup']({ point: { x: 120, y: 100 } });

    expect(onDrop).toHaveBeenCalledWith([99], 5);
  });

  test('multi-station drag label shows summed task count', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const getMultiSelectedStationIds = vi.fn(() => [10, 20, 30]);
    const getTaskCountForStation = vi.fn((stationId: number) => {
      const counts: Record<number, number> = { 10: 2, 20: 4, 30: 3 };
      return counts[stationId] ?? 0;
    });

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(10)]);

    initDragHandlers(
      mockMap,
      onDrop,
      undefined,
      getMultiSelectedStationIds,
      undefined,
      getTaskCountForStation
    );

    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      originalEvent: { shiftKey: false },
      preventDefault: vi.fn(),
    });

    // exceed threshold
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mousemove']({ point: { x: 108, y: 100 } });

    const ghost = document.querySelector('[data-testid="station-drag-ghost"]');
    expect(ghost).not.toBeNull();
    expect(ghost!.textContent).toBe('9 tasks');

    // cleanup
    mapHandlers['mouseup']({ point: { x: 108, y: 100 } });
  });

  test('shift+mousedown on station does not start drag (reserved for box select)', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(42)]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      originalEvent: { shiftKey: true },
      preventDefault: vi.fn(),
    });

    expect(onHighlight).not.toHaveBeenCalled();
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();
  });

  test('right-click mousedown on station does not start drag (reserved for box select)', () => {
    interceptWindowListeners();
    const { mockMap, mapHandlers } = createMockMap();
    const onDrop = vi.fn();
    const onHighlight = vi.fn();

    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([stationFeature(42)]);

    initDragHandlers(mockMap, onDrop, onHighlight);

    mapHandlers[`mousedown-${MapLayer.Stations}`]({
      point: { x: 100, y: 100 },
      originalEvent: { shiftKey: false, button: 2 },
      preventDefault: vi.fn(),
    });

    expect(onHighlight).not.toHaveBeenCalled();
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// setupMapClickHandlers - ctrl+click modifiers
// ---------------------------------------------------------------------------

describe('setupMapClickHandlers with modifiers', () => {
  function createMockMap(features: unknown[] = []) {
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
      queryRenderedFeatures: vi.fn(() => features),
    } as unknown as MapboxMap;
    return { mockMap, handlers };
  }

  test('ctrl+click on station passes ctrlKey: true in modifiers', () => {
    const { mockMap, handlers } = createMockMap([
      {
        layer: { id: MapLayer.Stations },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 1 },
      },
    ]);

    const onItemSelect = vi.fn();
    setupMapClickHandlers(mockMap, onItemSelect);

    handlers['click']({
      point: { x: 100, y: 100 },
      originalEvent: { ctrlKey: true, metaKey: false },
    });

    expect(onItemSelect).toHaveBeenCalledWith(
      expect.objectContaining({ type: SelectedItemType.Station, id: 1 }),
      { ctrlKey: true }
    );
  });

  test('meta+click (Mac Cmd) on station passes ctrlKey: true in modifiers', () => {
    const { mockMap, handlers } = createMockMap([
      {
        layer: { id: MapLayer.Stations },
        geometry: { type: 'Point', coordinates: [-73.5, 45.5] },
        properties: { id: 1 },
      },
    ]);

    const onItemSelect = vi.fn();
    setupMapClickHandlers(mockMap, onItemSelect);

    handlers['click']({
      point: { x: 100, y: 100 },
      originalEvent: { ctrlKey: false, metaKey: true },
    });

    expect(onItemSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1 }),
      { ctrlKey: true }
    );
  });

  test('clicking empty area with ctrl passes ctrlKey to null callback', () => {
    const { mockMap, handlers } = createMockMap([]);

    const onItemSelect = vi.fn();
    setupMapClickHandlers(mockMap, onItemSelect);

    handlers['click']({
      point: { x: 100, y: 100 },
      originalEvent: { ctrlKey: true, metaKey: false },
    });

    expect(onItemSelect).toHaveBeenCalledWith(null, { ctrlKey: true });
  });
});

// ---------------------------------------------------------------------------
// setupBoxSelectHandlers
// ---------------------------------------------------------------------------

describe('setupBoxSelectHandlers', () => {
  function createBoxSelectMockMap() {
    const mapHandlers: Record<string, (e: unknown) => void> = {};
    const parentElement = document.createElement('div');
    const canvasEventListeners: Record<string, EventListener[]> = {};
    const canvas = {
      style: { cursor: '' } as CSSStyleDeclaration,
      parentElement,
      addEventListener: vi.fn((event: string, handler: EventListener) => {
        if (!canvasEventListeners[event]) canvasEventListeners[event] = [];
        canvasEventListeners[event].push(handler);
      }),
      removeEventListener: vi.fn((event: string, handler: EventListener) => {
        if (canvasEventListeners[event]) {
          canvasEventListeners[event] = canvasEventListeners[event].filter(
            (h) => h !== handler
          );
        }
      }),
    };

    const mockMap = {
      on: vi.fn(
        (
          event: string,
          layerOrHandler: string | ((e: unknown) => void),
          handler?: (e: unknown) => void
        ) => {
          if (typeof layerOrHandler === 'function') {
            mapHandlers[event] = layerOrHandler;
          } else if (handler) {
            mapHandlers[`${event}-${layerOrHandler}`] = handler;
          }
        }
      ),
      off: vi.fn(),
      getCanvas: vi.fn(() => canvas),
      queryRenderedFeatures: vi.fn(() => []),
      boxZoom: { disable: vi.fn() },
      dragRotate: { disable: vi.fn() },
      dragPan: {
        enable: vi.fn(),
        disable: vi.fn(),
      },
    } as unknown as MapboxMap;

    return {
      mockMap,
      mapHandlers,
      canvas,
      parentElement,
      canvasEventListeners,
    };
  }

  test('disables boxZoom and dragRotate on setup', () => {
    const { mockMap } = createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    setupBoxSelectHandlers(mockMap, [MapLayer.Stations], onBoxSelect);

    expect(mockMap.boxZoom.disable).toHaveBeenCalled();
    expect(mockMap.dragRotate.disable).toHaveBeenCalled();
  });

  test('registers mousedown, mousemove, mouseup handlers', () => {
    const { mockMap } = createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    setupBoxSelectHandlers(mockMap, [MapLayer.Stations], onBoxSelect);

    expect(mockMap.on).toHaveBeenCalledWith('mousedown', expect.any(Function));
    expect(mockMap.on).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(mockMap.on).toHaveBeenCalledWith('mouseup', expect.any(Function));
  });

  test('shift+drag creates box select overlay and selects stations', () => {
    const { mockMap, mapHandlers, canvas, parentElement } =
      createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    setupBoxSelectHandlers(
      mockMap,
      [MapLayer.Stations, MapLayer.StationCircle],
      onBoxSelect
    );

    // shift+mousedown
    mapHandlers['mousedown']({
      point: { x: 50, y: 50 },
      originalEvent: { shiftKey: true },
      preventDefault: vi.fn(),
    });

    expect(canvas.style.cursor).toBe('crosshair');
    expect(mockMap.dragPan.disable).toHaveBeenCalled();

    // mousemove creates box overlay
    mapHandlers['mousemove']({
      point: { x: 150, y: 150 },
    });

    const overlay = parentElement.querySelector(
      '[data-testid="box-select-overlay"]'
    );
    expect(overlay).not.toBeNull();

    // mouseup queries features in box
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([
      { properties: { id: 1 } },
      { properties: { id: 2 } },
      { properties: { id: 1 } }, // duplicate
    ]);

    mapHandlers['mouseup']({
      point: { x: 150, y: 150 },
    });

    // Should call onBoxSelect with deduplicated station IDs
    expect(onBoxSelect).toHaveBeenCalledWith(expect.arrayContaining([1, 2]));
    expect(onBoxSelect.mock.calls[0][0]).toHaveLength(2);

    // Overlay should be removed
    expect(
      parentElement.querySelector('[data-testid="box-select-overlay"]')
    ).toBeNull();

    // dragPan should be re-enabled
    expect(mockMap.dragPan.enable).toHaveBeenCalled();
    expect(canvas.style.cursor).toBe('');
  });

  test('non-shift mousedown is ignored', () => {
    const { mockMap, mapHandlers, canvas } = createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    setupBoxSelectHandlers(mockMap, [MapLayer.Stations], onBoxSelect);

    mapHandlers['mousedown']({
      point: { x: 50, y: 50 },
      originalEvent: { shiftKey: false, button: 0 },
      preventDefault: vi.fn(),
    });

    expect(canvas.style.cursor).toBe('');
    expect(mockMap.dragPan.disable).not.toHaveBeenCalled();
  });

  test('right-click+drag creates box select overlay and selects stations', () => {
    const { mockMap, mapHandlers, canvas, parentElement } =
      createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    setupBoxSelectHandlers(
      mockMap,
      [MapLayer.Stations, MapLayer.StationCircle],
      onBoxSelect
    );

    // right-click mousedown (button === 2)
    mapHandlers['mousedown']({
      point: { x: 50, y: 50 },
      originalEvent: { shiftKey: false, button: 2 },
      preventDefault: vi.fn(),
    });

    expect(canvas.style.cursor).toBe('crosshair');
    expect(mockMap.dragPan.disable).toHaveBeenCalled();

    // mousemove creates box overlay
    mapHandlers['mousemove']({
      point: { x: 150, y: 150 },
    });

    const overlay = parentElement.querySelector(
      '[data-testid="box-select-overlay"]'
    );
    expect(overlay).not.toBeNull();

    // mouseup queries features in box
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([
      { properties: { id: 3 } },
      { properties: { id: 4 } },
    ]);

    mapHandlers['mouseup']({
      point: { x: 150, y: 150 },
    });

    expect(onBoxSelect).toHaveBeenCalledWith(expect.arrayContaining([3, 4]));
    expect(onBoxSelect.mock.calls[0][0]).toHaveLength(2);

    // Overlay should be removed
    expect(
      parentElement.querySelector('[data-testid="box-select-overlay"]')
    ).toBeNull();

    expect(mockMap.dragPan.enable).toHaveBeenCalled();
    expect(canvas.style.cursor).toBe('');
  });

  test('box select with no stations found does not call onBoxSelect', () => {
    const { mockMap, mapHandlers } = createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    setupBoxSelectHandlers(mockMap, [MapLayer.Stations], onBoxSelect);

    // shift+mousedown
    mapHandlers['mousedown']({
      point: { x: 50, y: 50 },
      originalEvent: { shiftKey: true },
      preventDefault: vi.fn(),
    });

    // mousemove
    mapHandlers['mousemove']({ point: { x: 150, y: 150 } });

    // mouseup with no features
    (
      mockMap.queryRenderedFeatures as ReturnType<typeof vi.fn>
    ).mockReturnValueOnce([]);
    mapHandlers['mouseup']({ point: { x: 150, y: 150 } });

    expect(onBoxSelect).not.toHaveBeenCalled();
  });

  test('cleanup removes event listeners', () => {
    const { mockMap } = createBoxSelectMockMap();
    const onBoxSelect = vi.fn();

    const cleanup = setupBoxSelectHandlers(
      mockMap,
      [MapLayer.Stations],
      onBoxSelect
    );

    cleanup();

    expect(mockMap.off).toHaveBeenCalledWith('mousedown', expect.any(Function));
    expect(mockMap.off).toHaveBeenCalledWith('mousemove', expect.any(Function));
    expect(mockMap.off).toHaveBeenCalledWith('mouseup', expect.any(Function));
  });
});
