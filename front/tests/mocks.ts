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

import { vi } from 'vitest';
import type LocalFrameSource from '~/lib/frame-sources/local-frame-source';
import type ServerFrameSource from '~/lib/frame-sources/server-frame-source';
import type MapManager from '~/lib/map-manager';
import type SimulationEngine from '~/lib/simulation-engine';
import type SimulationStateManager from '~/lib/simulation-state-manager';
import type { Position } from '~/types';

type eventType = 'load' | 'move' | 'error';

export class MockMap {
  static instance: undefined | MockMap;
  private container: string | HTMLElement;
  private center: Position;
  private zoom: number;
  private style: string;
  public callBacks: Record<eventType, (arg?: unknown) => void> = {
    move: () => {},
    load: () => {},
    error: () => {},
  };
  constructor({
    container,
    center,
    zoom,
    style,
  }: {
    container: string | HTMLElement;
    center: Position;
    zoom: number;
    style: string;
  }) {
    MockMap.instance = this;
    this.center = center;
    this.zoom = zoom;
    this.style = style;
    this.container = container;
  }
  on = vi.fn((type: eventType, cb: (arg?: unknown) => void) => {
    this.callBacks[type] = cb;
  });
  once = vi.fn((type: eventType, cb: (arg?: unknown) => void) => {
    this.callBacks[type] = cb;
  });
  remove = vi.fn();
  getCenter = vi.fn(() => this.center);
  getZoom = vi.fn(() => this.zoom);
  move = () => {
    this.callBacks['move']();
  };
  loadImage = vi.fn();
  addImage = vi.fn();
  addSource = vi.fn();
  addLayer = vi.fn();
  getSource = vi.fn();
  isStyleLoaded = vi.fn(() => true);
  static clear() {
    MockMap.instance = undefined;
  }
  static createRandomInstance() {
    MockMap.instance = new MockMap({
      container: 'container',
      center: [Math.random() * 100, Math.random() * 100],
      zoom: Math.random() * 20,
      style: 'style',
    });
  }
}

export const mockDisplayError = vi.fn();

export const consoleErrorSpy = vi
  .spyOn(console, 'error')
  .mockImplementation(() => {});

export const mockLocalFrameSource: Partial<LocalFrameSource> = {
  setSpeed: vi.fn(),
  getFrame: vi.fn(),
  getMaxFrame: vi.fn(),
  setPosition: vi.fn(),
};
export const MockLocalFrameSource = vi
  .fn()
  .mockImplementation(() => mockLocalFrameSource);

export const mockServerFrameSource: Partial<ServerFrameSource> = {
  start: vi.fn().mockResolvedValue(true),
  stop: vi.fn(),
  setSpeed: vi.fn(),
};
export const MockServerFrameSource = vi
  .fn()
  .mockImplementation(() => mockServerFrameSource);

export const mockSimulationEngine: Partial<SimulationEngine> = {
  hasStarted: vi.fn().mockReturnValue(false),
  setPaused: vi.fn(),
  setSpeed: vi.fn(),
  selectItem: vi.fn(),
  clearSelection: vi.fn(),
  confirmAssignment: vi.fn(),
  cancelAssignment: vi.fn(),
  reorderTasks: vi.fn(),
  requestUnassignment: vi.fn(),
  destroy: vi.fn(),
};
export const MockSimulationEngine = vi
  .fn()
  .mockImplementation(() => mockSimulationEngine);

export const mockSimulationStateManager: Partial<SimulationStateManager> = {
  getDriver: vi.fn(),
  getAllDrivers: vi.fn().mockReturnValue([]),
  setDriver: vi.fn(),

  getStation: vi.fn(),
  getAllStations: vi.fn().mockReturnValue([]),
  setStation: vi.fn(),

  getVehicle: vi.fn(),
  getAllVehicles: vi.fn().mockReturnValue([]),
  setVehicle: vi.fn(),

  getTask: vi.fn(),
  setTask: vi.fn(),

  getSelectedItems: vi.fn().mockReturnValue([]),
  setSelectedItem: vi.fn(),

  addSelectedStation: vi.fn(),
  removeSelectedStation: vi.fn(),
  toggleSelectedStation: vi.fn(),
  setSelectedStations: vi.fn(),
  clearSelection: vi.fn(),

  getMultiSelectedStationIds: vi.fn().mockReturnValue(new Set()),
  getPartialAssignmentStationIds: vi.fn().mockReturnValue(new Set()),

  getHeadquarters: vi.fn(),
  setHeadquarters: vi.fn(),

  getMapShouldRefresh: vi.fn(),
  setMapShouldRefresh: vi.fn(),

  getLoading: vi.fn(),
  setLoading: vi.fn(),

  getBlockAssignments: vi.fn().mockReturnValue(false),
  setBlockAssignments: vi.fn(),

  getPendingAssignment: vi.fn(),
  setPendingAssignment: vi.fn(),

  getPendingAssignmentLoading: vi.fn(),
  setPendingAssignmentLoading: vi.fn(),

  getFormattedSimTime: vi.fn(),
  setFormattedSimTime: vi.fn(),

  getCurrentDay: vi.fn(),
  setCurrentDay: vi.fn(),

  getNonZeroSpeed: vi.fn(),
  setNonZeroSpeed: vi.fn(),

  getPaused: vi.fn(),
  setPaused: vi.fn(),

  getShowAllRoutes: vi.fn(),
  setShowAllRoutes: vi.fn(),

  getStartTime: vi.fn(),
  setStartTime: vi.fn(),

  getSimulationSecondsPassed: vi.fn(),
  setSimulationSecondsPassed: vi.fn(),

  getScrubSimulationSecond: vi.fn(),
  setScrubSimulationSecond: vi.fn(),

  updateHQWidgetState: vi.fn(),
};
export const MockSimulationStateManager = vi
  .fn()
  .mockImplementation(() => mockSimulationStateManager);

export const mockMapManager: Partial<MapManager> = {
  processFrame: vi.fn(),
};
export const MockMapManager = vi.fn().mockImplementation(() => mockMapManager);
