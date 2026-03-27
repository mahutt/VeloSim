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

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DriverTasks } from '~/components/map/driver-tasks';
import { useSimulation } from '~/providers/simulation-provider';
import {
  makePopulatedDriver,
  makeReactiveSimulationState,
  makeSimulationContext,
  makeStationTask,
} from 'tests/test-helpers';
import { mockSimulationEngine } from 'tests/mocks';
import type SimulationEngine from '~/lib/simulation-engine';

vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('DriverTasks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function setupDriverTasks({
    driver,
    stationNames,
  }: {
    driver?: ReturnType<typeof makePopulatedDriver>;
    stationNames?: Record<number, string>;
  } = {}) {
    vi.mocked(useSimulation).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          blockAssignments: false,
        }),
        engine: {
          ...mockSimulationEngine,
          state: {
            getStation: (stationId: number) => {
              const name = stationNames?.[stationId];
              return name ? { id: stationId, name } : undefined;
            },
          },
        } as unknown as SimulationEngine,
      })
    );

    return render(
      <DriverTasks
        driver={
          driver ??
          makePopulatedDriver({
            id: 7,
            tasks: [makeStationTask({ id: 1, stationId: 1 })],
          })
        }
      />
    );
  }

  it('toggles between expanded and collapsed modes', async () => {
    const user = userEvent.setup();

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 8,
        tasks: [makeStationTask({ id: 11, stationId: 1 })],
      }),
      stationNames: { 1: 'Station A' },
    });

    expect(screen.getByText('Station A')).toBeInTheDocument();
    const expandToggle = screen.getByRole('button', {
      name: 'Expand task list',
    });
    await user.click(expandToggle);

    expect(screen.getByText(/^#\s*11$/)).toBeInTheDocument();
    expect(screen.getByText('Station A')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Collapse task list' })
    ).toBeInTheDocument();
  });

  it('groups contiguous station runs in collapsed mode', () => {
    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 9,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({ id: 2, stationId: 2 }),
          makeStationTask({ id: 3, stationId: 2 }),
          makeStationTask({ id: 4, stationId: 1 }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B' },
    });

    expect(screen.getAllByText('Station A')).toHaveLength(2);
    expect(screen.getAllByText('Station B')).toHaveLength(1);
    expect(screen.getAllByText('1 task')).toHaveLength(2);
    expect(screen.getByText('2 tasks')).toBeInTheDocument();
  });

  it('uses Station #ID fallback when station name is missing', () => {
    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 10,
        tasks: [makeStationTask({ id: 100, stationId: 99 })],
      }),
    });

    expect(screen.getByText('Station #99')).toBeInTheDocument();
  });

  it('reorders collapsed groups and sends flattened task IDs', async () => {
    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 12,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({ id: 2, stationId: 1 }),
          makeStationTask({ id: 3, stationId: 2 }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B' },
    });

    const stationADraggable = screen
      .getAllByText('Station A')[0]
      .closest('[draggable="true"]') as HTMLElement;
    const stationBWrapper = screen
      .getByText('Station B')
      .closest('[draggable="true"]')?.parentElement as HTMLElement;

    fireEvent.dragStart(stationADraggable, {
      dataTransfer: { effectAllowed: '', dropEffect: '' },
    });
    fireEvent.dragOver(stationBWrapper, {
      dataTransfer: { dropEffect: '' },
    });
    fireEvent.drop(stationBWrapper);

    await waitFor(() => {
      expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
        12,
        [3, 1, 2],
        true
      );
    });
  });

  it('does not reorder collapsed groups when dropped on same index', () => {
    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 13,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({ id: 2, stationId: 2 }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B' },
    });

    const stationADraggable = screen
      .getByText('Station A')
      .closest('[draggable="true"]') as HTMLElement;
    const stationAWrapper = stationADraggable.parentElement as HTMLElement;

    fireEvent.dragStart(stationADraggable, {
      dataTransfer: { effectAllowed: '', dropEffect: '' },
    });
    fireEvent.drop(stationAWrapper);

    expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();
  });

  describe('non-contiguous multi-group reorder', () => {
    const stationNames: Record<number, string> = {
      1: 'Station A',
      2: 'Station B',
      3: 'Station C',
      4: 'Station D',
      5: 'Station E',
    };

    async function setupCollapsedWithFiveGroups() {
      const user = userEvent.setup();

      setupDriverTasks({
        driver: makePopulatedDriver({
          id: 20,
          tasks: [
            makeStationTask({ id: 10, stationId: 1 }),
            makeStationTask({ id: 20, stationId: 2 }),
            makeStationTask({ id: 30, stationId: 3 }),
            makeStationTask({ id: 40, stationId: 4 }),
            makeStationTask({ id: 50, stationId: 5 }),
          ],
        }),
        stationNames,
      });

      return user;
    }

    function getGroupElements() {
      return [
        'Station A',
        'Station B',
        'Station C',
        'Station D',
        'Station E',
      ].map((name) => {
        const draggable = screen
          .getByText(name)
          .closest('[draggable="true"]') as HTMLElement;
        const wrapper = draggable.parentElement as HTMLElement;
        return { draggable, wrapper };
      });
    }

    it('moves groups at indices 1 and 3 forward past the last group', async () => {
      await setupCollapsedWithFiveGroups();
      const groups = getGroupElements();

      // Ctrl+click group B (index 1) then Ctrl+click group D (index 3)
      fireEvent.click(groups[1].wrapper, { ctrlKey: true });
      fireEvent.click(groups[3].wrapper, { ctrlKey: true });

      // Drag group B (sourceIndex=1) → drop on group E (targetIndex=4)
      fireEvent.dragStart(groups[1].draggable, {
        dataTransfer: { effectAllowed: '', dropEffect: '' },
      });
      fireEvent.dragOver(groups[4].wrapper, {
        dataTransfer: { dropEffect: '' },
      });
      fireEvent.drop(groups[4].wrapper);

      // Expected: A, C, E, B, D → [10, 30, 50, 20, 40]
      await waitFor(() => {
        expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
          20,
          [10, 30, 50, 20, 40],
          true
        );
      });
    });

    it('moves groups at indices 1 and 3 backward before the first group', async () => {
      await setupCollapsedWithFiveGroups();
      const groups = getGroupElements();

      fireEvent.click(groups[1].wrapper, { ctrlKey: true });
      fireEvent.click(groups[3].wrapper, { ctrlKey: true });

      // Drag group D (sourceIndex=3) → drop on group A (targetIndex=0)
      fireEvent.dragStart(groups[3].draggable, {
        dataTransfer: { effectAllowed: '', dropEffect: '' },
      });
      fireEvent.dragOver(groups[0].wrapper, {
        dataTransfer: { dropEffect: '' },
      });
      fireEvent.drop(groups[0].wrapper);

      // Expected: B, D, A, C, E → [20, 40, 10, 30, 50]
      await waitFor(() => {
        expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
          20,
          [20, 40, 10, 30, 50],
          true
        );
      });
    });

    it('moves groups at indices 1 and 3 to a position between them', async () => {
      await setupCollapsedWithFiveGroups();
      const groups = getGroupElements();

      fireEvent.click(groups[1].wrapper, { ctrlKey: true });
      fireEvent.click(groups[3].wrapper, { ctrlKey: true });

      // Drag group B (sourceIndex=1) → drop on group C (targetIndex=2, between the selections)
      fireEvent.dragStart(groups[1].draggable, {
        dataTransfer: { effectAllowed: '', dropEffect: '' },
      });
      fireEvent.dragOver(groups[2].wrapper, {
        dataTransfer: { dropEffect: '' },
      });
      fireEvent.drop(groups[2].wrapper);

      // Expected: A, C, B, D, E → [10, 30, 20, 40, 50]
      await waitFor(() => {
        expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
          20,
          [10, 30, 20, 40, 50],
          true
        );
      });
    });
  });

  it('requests unassignment from collapsed view', async () => {
    const user = userEvent.setup();

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 15,
        tasks: [makeStationTask({ id: 44, stationId: 3 })],
      }),
      stationNames: { 3: 'Station C' },
    });

    await user.click(
      screen.getByRole('button', { name: 'Unassign 1 task at Station C' })
    );

    expect(mockSimulationEngine.requestUnassignment).toHaveBeenCalledWith(
      15,
      [44],
      'Station C'
    );
  });
});
