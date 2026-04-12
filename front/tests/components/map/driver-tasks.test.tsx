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
import {
  createEvent,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
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
import { TaskState } from '~/types';

vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('DriverTasks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function createMockDataTransfer() {
    const store = new Map<string, string>();

    return {
      effectAllowed: '',
      dropEffect: '',
      setData: vi.fn((key: string, value: string) => {
        store.set(key, value);
      }),
      getData: vi.fn((key: string) => store.get(key) ?? ''),
      setDragImage: vi.fn(),
    };
  }

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

  it('sets hovered station on task hover in expanded mode', async () => {
    const user = userEvent.setup();

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 2,
        tasks: [makeStationTask({ id: 101, stationId: 42 })],
      }),
      stationNames: { 50: 'Station Z' },
    });

    await user.click(
      screen.getByRole('button', {
        name: 'Expand task list',
      })
    );

    const taskDraggable = screen
      .getByText(/^#\s*101$/)
      .closest('[draggable="true"]') as HTMLElement;
    const taskWrapper = taskDraggable.parentElement as HTMLElement;

    fireEvent.mouseEnter(taskWrapper);

    expect(mockSimulationEngine.setTaskHoveredStationId).toHaveBeenCalledWith(
      42
    );
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

    const dataTransfer = createMockDataTransfer();

    fireEvent.dragStart(stationADraggable, {
      dataTransfer,
    });
    fireEvent.dragOver(stationBWrapper, {
      dataTransfer,
    });
    fireEvent.drop(stationBWrapper, { dataTransfer });

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
    const dataTransfer = createMockDataTransfer();

    fireEvent.dragStart(stationADraggable, {
      dataTransfer,
    });
    fireEvent.drop(stationAWrapper, { dataTransfer });

    expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();
  });

  it('renders servicing collapsed groups as disabled and non-interactive', async () => {
    const user = userEvent.setup();

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 16,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({
            id: 2,
            stationId: 2,
            state: TaskState.InService,
          }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B' },
    });

    const stationBDraggable = screen
      .getByText('Station B')
      .closest('[draggable="false"]') as HTMLElement;
    const stationBWrapper = stationBDraggable.parentElement as HTMLElement;

    expect(stationBDraggable).toHaveClass('opacity-50');

    await user.click(stationBWrapper);

    expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();

    const stationADraggable = screen
      .getByText('Station A')
      .closest('[draggable="true"]') as HTMLElement;
    fireEvent.dragStart(stationADraggable, {
      dataTransfer: { effectAllowed: '', dropEffect: '' },
    });
    fireEvent.dragOver(stationBWrapper, {
      dataTransfer: { dropEffect: '' },
    });
    fireEvent.drop(stationBWrapper);

    expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();
  });

  it('blocks collapsed reordering when it would move an in-service station group', () => {
    const inServiceTask = makeStationTask({
      id: 2,
      stationId: 2,
      state: TaskState.InService,
    });

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 14,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          inServiceTask,
          makeStationTask({ id: 3, stationId: 3 }),
        ],
        inProgressTask: inServiceTask,
      }),
      stationNames: { 1: 'Station A', 2: 'Station B', 3: 'Station C' },
    });

    const stationADraggable = screen
      .getByText('Station A')
      .closest('[draggable="true"]') as HTMLElement;
    const stationCWrapper = screen
      .getByText('Station C')
      .closest('[draggable="true"]')?.parentElement as HTMLElement;
    const dataTransfer = createMockDataTransfer();

    fireEvent.dragStart(stationADraggable, { dataTransfer });
    fireEvent.dragOver(stationCWrapper, { dataTransfer });
    fireEvent.drop(stationCWrapper, { dataTransfer });

    expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();
  });

  it('allows collapsed reordering when it would not move an in-service station group', () => {
    const inServiceTask = makeStationTask({
      id: 1,
      stationId: 1,
      state: TaskState.InService,
    });

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 14,
        tasks: [
          inServiceTask,
          makeStationTask({ id: 2, stationId: 2 }),
          makeStationTask({ id: 3, stationId: 3 }),
        ],
        inProgressTask: inServiceTask,
      }),
      stationNames: { 1: 'Station A', 2: 'Station B', 3: 'Station C' },
    });

    const stationBDraggable = screen
      .getByText('Station B')
      .closest('[draggable="true"]') as HTMLElement;
    const stationCWrapper = screen
      .getByText('Station C')
      .closest('[draggable="true"]')?.parentElement as HTMLElement;
    const dataTransfer = createMockDataTransfer();

    fireEvent.dragStart(stationBDraggable, { dataTransfer });
    fireEvent.dragOver(stationCWrapper, { dataTransfer });
    fireEvent.drop(stationCWrapper, { dataTransfer });

    expect(mockSimulationEngine.reorderTasks).toHaveBeenCalled();
  });

  it('starts collapsed drag selection on right mouse down', () => {
    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 17,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({ id: 2, stationId: 2 }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B' },
    });

    const stationAWrapper = screen
      .getByText('Station A')
      .closest('[draggable="true"]')?.parentElement as HTMLElement;

    fireEvent.mouseDown(stationAWrapper, { button: 2, ctrlKey: true });

    expect(mockSimulationEngine.setTaskHoveredStationId).not.toHaveBeenCalled();
  });

  it('prevents expanded reorder drag-over on an in-service task', async () => {
    const user = userEvent.setup();

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 18,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({
            id: 2,
            stationId: 2,
            state: TaskState.InService,
          }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B' },
    });

    await user.click(
      screen.getByRole('button', {
        name: 'Expand task list',
      })
    );

    const task1Draggable = screen
      .getByText('#1')
      .closest('[draggable="true"]') as HTMLElement;
    const task2Draggable = screen
      .getByText('#2')
      .closest('[draggable="false"]') as HTMLElement;
    const task2Wrapper = task2Draggable.parentElement as HTMLElement;
    const dataTransfer = createMockDataTransfer();

    fireEvent.dragStart(task1Draggable, { dataTransfer });
    const dragOverEvent = createEvent.dragOver(task2Wrapper);
    Object.defineProperty(dragOverEvent, 'dataTransfer', {
      value: dataTransfer,
    });
    fireEvent(task2Wrapper, dragOverEvent);

    expect(dragOverEvent.defaultPrevented).toBe(true);
    expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();
  });

  it('reorders a single expanded task when the dragged task is not already selected', async () => {
    const user = userEvent.setup();

    setupDriverTasks({
      driver: makePopulatedDriver({
        id: 19,
        tasks: [
          makeStationTask({ id: 1, stationId: 1 }),
          makeStationTask({ id: 2, stationId: 2 }),
          makeStationTask({ id: 3, stationId: 3 }),
        ],
      }),
      stationNames: { 1: 'Station A', 2: 'Station B', 3: 'Station C' },
    });

    await user.click(
      screen.getByRole('button', {
        name: 'Expand task list',
      })
    );

    const task1Draggable = screen
      .getByText('#1')
      .closest('[draggable="true"]') as HTMLElement;
    const task3Draggable = screen
      .getByText('#3')
      .closest('[draggable="true"]') as HTMLElement;
    const task3Wrapper = task3Draggable.parentElement as HTMLElement;
    const dataTransfer = createMockDataTransfer();

    fireEvent.dragStart(task1Draggable, { dataTransfer });
    fireEvent.dragOver(task3Wrapper, { dataTransfer });
    fireEvent.drop(task3Wrapper, { dataTransfer });

    await waitFor(() => {
      expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
        19,
        [2, 3, 1],
        true
      );
    });
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
      const dataTransfer = createMockDataTransfer();

      // Ctrl+click group B (index 1) then Ctrl+click group D (index 3)
      fireEvent.click(groups[1].wrapper, { ctrlKey: true });
      fireEvent.click(groups[3].wrapper, { ctrlKey: true });

      // Drag group B (sourceIndex=1) → drop on group E (targetIndex=4)
      fireEvent.dragStart(groups[1].draggable, {
        dataTransfer,
      });
      fireEvent.dragOver(groups[4].wrapper, {
        dataTransfer,
      });
      fireEvent.drop(groups[4].wrapper, { dataTransfer });

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
      const dataTransfer = createMockDataTransfer();

      fireEvent.click(groups[1].wrapper, { ctrlKey: true });
      fireEvent.click(groups[3].wrapper, { ctrlKey: true });

      // Drag group D (sourceIndex=3) → drop on group A (targetIndex=0)
      fireEvent.dragStart(groups[3].draggable, {
        dataTransfer,
      });
      fireEvent.dragOver(groups[0].wrapper, {
        dataTransfer,
      });
      fireEvent.drop(groups[0].wrapper, { dataTransfer });

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
      const dataTransfer = createMockDataTransfer();

      fireEvent.click(groups[1].wrapper, { ctrlKey: true });
      fireEvent.click(groups[3].wrapper, { ctrlKey: true });

      // Drag group B (sourceIndex=1) → drop on group C (targetIndex=2, between the selections)
      fireEvent.dragStart(groups[1].draggable, {
        dataTransfer,
      });
      fireEvent.dragOver(groups[2].wrapper, {
        dataTransfer,
      });
      fireEvent.drop(groups[2].wrapper, { dataTransfer });

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
