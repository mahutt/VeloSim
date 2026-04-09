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

import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import api from '~/api';
import { USER_PREFERENCES_STORAGE_KEY } from '~/constants';
import {
  EN_TRANSLATIONS,
  FR_TRANSLATIONS,
  formatTranslation,
} from '~/lib/i18n';
import SimulationEngine from '~/lib/simulation-engine';
import { TaskAction, UILanguage } from '~/types';
import {
  makeDriver,
  makePendingAssignment,
  makeReactiveSimulationState,
  makeStationTask,
} from 'tests/test-helpers';

const {
  mockToastError,
  mockSimulationStateManager,
  MockSimulationStateManager,
  MockMapManager,
  MockLocalFrameSource,
  MockServerFrameSource,
} = await vi.hoisted(async () => {
  const mocks = await import('tests/mocks');
  return {
    ...mocks,
    mockToastError: vi.fn(),
  };
});

vi.mock('sonner', () => ({
  toast: {
    error: mockToastError,
  },
}));
vi.mock('~/api', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));
vi.mock('~/lib/map-manager', () => ({
  default: MockMapManager,
}));
vi.mock('~/lib/simulation-state-manager', () => ({
  default: MockSimulationStateManager,
}));
vi.mock('~/lib/frame-sources/local-frame-source', () => ({
  default: MockLocalFrameSource,
}));
vi.mock('~/lib/frame-sources/server-frame-source', () => ({
  default: MockServerFrameSource,
}));

const mockMap = {} as unknown as mapboxgl.Map;

describe('SimulationEngine i18n runtime behavior', () => {
  let engine: SimulationEngine;

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();

    engine = new SimulationEngine(
      'test_simulation',
      mockMap,
      makeReactiveSimulationState(),
      () => {}
    );
  });

  it('uses the latest stored language for assignment error toasts without recreating engine', async () => {
    const driverId = 1;
    const taskIds = [1, 2];

    (mockSimulationStateManager.getPendingAssignment as Mock).mockReturnValue(
      makePendingAssignment({
        action: TaskAction.Assign,
        taskIds,
        driverId,
      })
    );
    (
      mockSimulationStateManager.getPendingAssignmentLoading as Mock
    ).mockReturnValue(false);
    (mockSimulationStateManager.getDriver as Mock).mockReturnValue(
      makeDriver({ id: driverId })
    );
    (mockSimulationStateManager.getTask as Mock).mockReturnValue(
      makeStationTask()
    );
    (api.post as Mock).mockRejectedValue(new Error('Network error'));

    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    sessionStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: UILanguage.English })
    );
    await engine.confirmAssignment();

    expect(mockToastError).toHaveBeenNthCalledWith(
      1,
      formatTranslation(
        EN_TRANSLATIONS.map.assignment.errors.batchAssignmentFailed,
        {
          count: taskIds.length,
        }
      )
    );

    sessionStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: UILanguage.French })
    );
    await engine.confirmAssignment();

    expect(mockToastError).toHaveBeenNthCalledWith(
      2,
      formatTranslation(
        FR_TRANSLATIONS.map.assignment.errors.batchAssignmentFailed,
        {
          count: taskIds.length,
        }
      )
    );

    consoleErrorSpy.mockRestore();
  });

  it('uses the latest stored language for unassignment error toasts without recreating engine', async () => {
    const driverId = 1;
    const taskId = 42;

    (mockSimulationStateManager.getPendingAssignment as Mock).mockReturnValue(
      makePendingAssignment({
        action: TaskAction.Unassign,
        taskIds: [taskId],
        driverId,
      })
    );
    (
      mockSimulationStateManager.getPendingAssignmentLoading as Mock
    ).mockReturnValue(false);
    (mockSimulationStateManager.getDriver as Mock).mockReturnValue(
      makeDriver({ id: driverId })
    );
    (api.post as Mock).mockRejectedValue(new Error('Network error'));

    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    sessionStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: UILanguage.English })
    );
    await engine.confirmAssignment();

    expect(mockToastError).toHaveBeenNthCalledWith(
      1,
      formatTranslation(
        EN_TRANSLATIONS.map.assignment.errors.batchUnassignmentFailed,
        {
          count: 1,
        }
      )
    );

    sessionStorage.setItem(
      USER_PREFERENCES_STORAGE_KEY,
      JSON.stringify({ language: UILanguage.French })
    );
    await engine.confirmAssignment();

    expect(mockToastError).toHaveBeenNthCalledWith(
      2,
      formatTranslation(
        FR_TRANSLATIONS.map.assignment.errors.batchUnassignmentFailed,
        {
          count: 1,
        }
      )
    );

    consoleErrorSpy.mockRestore();
  });
});
