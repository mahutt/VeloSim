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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useSimulation } from '~/providers/simulation-provider';
import SelectedItemBar, {
  SelectedItemType,
} from '~/components/map/selected-item-bar';
import { FeatureToggleProvider } from '~/providers/feature-toggle-provider';
import {
  makePopulatedDriver,
  makePopulatedStation,
  makeReactiveSimulationState,
  makeSelectedItem,
  makeSimulationContext,
  makeStationTask,
} from 'tests/test-helpers';
import { mockSimulationEngine } from 'tests/mocks';
import type SimulationEngine from '~/lib/simulation-engine';

// Mock the useSimulation hook
vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('SelectedItemBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when no item is selected', () => {
    vi.mocked(useSimulation).mockReturnValue(makeSimulationContext());

    const { container } = render(
      <FeatureToggleProvider>
        <SelectedItemBar />
      </FeatureToggleProvider>
    );
    expect(container.firstChild).toBeNull();
  });

  it('should render station information when station is selected', () => {
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          selectedItems: [
            makeSelectedItem({
              type: SelectedItemType.Station,
              value: makePopulatedStation({
                id: 1,
                name: 'Test Station',
                tasks: [],
              }),
            }),
          ],
        }),
      })
    );

    render(
      <FeatureToggleProvider>
        <SelectedItemBar />
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Station #1')).toBeInTheDocument();
    expect(screen.getByText('Test Station')).toBeInTheDocument();
    expect(screen.getByText('No tasks')).toBeInTheDocument();
  });

  it('should render driver information when driver is selected', () => {
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          selectedItems: [
            makeSelectedItem({
              type: SelectedItemType.Driver,
              value: makePopulatedDriver({
                id: 5,
                name: 'Driver 5',
                tasks: [
                  makeStationTask({ id: 1 }),
                  makeStationTask({ id: 2 }),
                  makeStationTask({ id: 3 }),
                ],
              }),
            }),
          ],
        }),
      })
    );

    render(
      <FeatureToggleProvider>
        <SelectedItemBar />
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Driver 5')).toBeInTheDocument();
    expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
    expect(screen.getByText(/Station\s*#1/)).toBeInTheDocument();
    expect(screen.getByText(/3\s*tasks/)).toBeInTheDocument();
  });

  it('should call clearSelection when close button is clicked', async () => {
    const user = userEvent.setup();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          selectedItems: [
            makeSelectedItem({
              type: SelectedItemType.Station,
              value: makePopulatedStation(),
            }),
          ],
        }),
        engine: mockSimulationEngine as SimulationEngine,
      })
    );

    render(
      <FeatureToggleProvider>
        <SelectedItemBar />
      </FeatureToggleProvider>
    );

    const closeButton = screen.getByRole('button');
    await user.click(closeButton);

    expect(mockSimulationEngine.clearSelection).toHaveBeenCalledTimes(1);
  });

  it('should display tasks when station has tasks', () => {
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          selectedItems: [
            makeSelectedItem({
              type: SelectedItemType.Station,
              value: makePopulatedStation({
                id: 1,
                name: 'Test Station',
                tasks: [makeStationTask({ id: 1 }), makeStationTask({ id: 2 })],
              }),
            }),
          ],
        }),
      })
    );

    render(
      <FeatureToggleProvider>
        <SelectedItemBar />
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
    const taskItems = screen.getAllByText(/^#/);
    expect(taskItems).toHaveLength(2);
  });

  describe('Task Reordering', () => {
    it('should call reorderTasks when task is dropped at a valid position', async () => {
      (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      // Get the task wrappers
      const taskElements = screen
        .getAllByText(/^#/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Simulate dragstart on task 1
      fireEvent.dragStart(taskElements[0]);

      // Simulate drop on task 3 wrapper (index 2)
      fireEvent.drop(taskWrappers[2]);

      // Should reorder: [2, 3, 1]
      expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
        1,
        [2, 3, 1],
        true
      );
    });

    it('should set dropEffect to none when draggedTaskId is null', () => {
      (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      const taskElements = screen
        .getAllByText(/^#/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Simulate dragover WITHOUT dragstart (draggedTaskId will be null)
      const dragOverEvent = fireEvent.dragOver(taskWrappers[1]);

      expect(dragOverEvent).toBe(false); // Event should be prevented but dropEffect set to 'none'
    });
  });

  describe('Multi-Selection', () => {
    it('should render multi-station view when multiple stations are selected', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 1,
                  name: 'Station Alpha',
                  tasks: [
                    makeStationTask({ id: 10 }),
                    makeStationTask({ id: 11 }),
                  ],
                }),
              }),
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 2,
                  name: 'Station Beta',
                  tasks: [makeStationTask({ id: 20 })],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      expect(screen.getByText('2 Stations (3 tasks)')).toBeInTheDocument();
      expect(screen.getByText('Station Alpha')).toBeInTheDocument();
      expect(screen.getByText('Station Beta')).toBeInTheDocument();
      expect(screen.getByText('(2 tasks)')).toBeInTheDocument();
      expect(screen.getByText('(1 tasks)')).toBeInTheDocument();
    });

    it('should call clearSelection when close button is clicked in multi-selection view', async () => {
      const user = userEvent.setup();
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({ id: 1, name: 'S1' }),
              }),
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({ id: 2, name: 'S2' }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      const closeButton = screen.getByRole('button');
      await user.click(closeButton);

      expect(mockSimulationEngine.clearSelection).toHaveBeenCalledTimes(1);
    });

    it('should show zero tasks for stations with no tasks', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 1,
                  name: 'Empty A',
                  tasks: [],
                }),
              }),
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 2,
                  name: 'Empty B',
                  tasks: [],
                }),
              }),
            ],
          }),
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      expect(screen.getByText('2 Stations (0 tasks)')).toBeInTheDocument();
    });
  });

  describe('StationTasks', () => {
    it('should show selected count when tasks are ctrl+clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 1,
                  name: 'Test Station',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      // Ctrl+click to select a station task
      const taskItems = screen.getAllByText(/^#/);
      const firstItem = taskItems[0].closest(
        '[data-slot="item"]'
      ) as HTMLElement;
      await user.keyboard('{Meta>}');
      await user.click(firstItem);
      await user.keyboard('{/Meta}');

      expect(screen.getByText('Tasks (1/3 selected)')).toBeInTheDocument();
    });

    it('should call getDragTaskIds during dragStart on station task', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 1,
                  name: 'Test Station',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      const taskItems = screen.getAllByText(/^#/);
      const firstItem = taskItems[0].closest(
        '[data-slot="item"]'
      ) as HTMLElement;

      const setDataMock = vi.fn();
      fireEvent.dragStart(firstItem, {
        dataTransfer: { setData: setDataMock, effectAllowed: '' },
      });

      // getDragTaskIds should have been invoked and setData called with the resulting task ids
      expect(setDataMock).toHaveBeenCalledWith('taskIds', expect.any(String));
    });

    it('should start drag select on right-click (mousedown button=2) on a station task', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 1,
                  name: 'Test Station',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      const taskItems = screen.getAllByText(/^#/);
      // The wrapper div containing the task item (one level up from [data-slot="item"])
      const firstWrapper = taskItems[0].closest('[data-slot="item"]')!
        .parentElement as HTMLElement;

      fireEvent.mouseDown(firstWrapper, { button: 2 });

      // After right-click drag start, task 1 should be selected
      expect(screen.getByText('Tasks (1/3 selected)')).toBeInTheDocument();
    });

    it('should call requestUnassignment when unassign button is clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: makePopulatedStation({
                  id: 1,
                  name: 'Test Station',
                  tasks: [
                    makeStationTask({ id: 10, assignedDriverId: 5 }),
                    makeStationTask({ id: 11 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      // The assigned task should have an unassign button (X)
      const unassignButtons = screen.getAllByRole('button');
      // First button is the close (X) for the sidebar, subsequent ones are task unassign buttons
      // Find the small unassign button within the task items
      const taskUnassignButton = unassignButtons.find(
        (btn) => btn.closest('[data-slot="item"]') !== null
      );
      expect(taskUnassignButton).toBeDefined();
      await user.click(taskUnassignButton!);

      expect(mockSimulationEngine.requestUnassignment).toHaveBeenCalledWith(
        5,
        10
      );
    });
  });

  describe('DriverTasks', () => {
    it('should show selected count when tasks are ctrl+clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      // Ctrl+click to select a driver task
      const taskItems = screen.getAllByText(/^#/);
      const firstItem = taskItems[0].closest(
        '[data-slot="item"]'
      ) as HTMLElement;
      await user.keyboard('{Meta>}');
      await user.click(firstItem);
      await user.keyboard('{/Meta}');

      expect(screen.getByText('Tasks (1/3 selected)')).toBeInTheDocument();
    });

    it('should call getDragTaskIds during dragStart on driver task', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      const taskItems = screen.getAllByText(/^#/);
      const firstItem = taskItems[0].closest(
        '[data-slot="item"]'
      ) as HTMLElement;

      const setDataMock = vi.fn();
      fireEvent.dragStart(firstItem, {
        dataTransfer: { setData: setDataMock, effectAllowed: '' },
      });

      // getDragTaskIds should have been invoked and setData called with the resulting task ids
      expect(setDataMock).toHaveBeenCalledWith('taskIds', expect.any(String));
    });

    it('should reorder correctly when dragging a task upward', async () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      // This test is intended to act on the expanded task view
      const collapseToggle = screen.getByRole('button', {
        name: 'Expand task list',
      });
      fireEvent.click(collapseToggle);

      const taskElements = screen
        .getAllByText(/^#/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Drag task 3 (index 2) and drop on task 1 (index 0) — dragging upward
      fireEvent.dragStart(taskElements[2]);
      fireEvent.drop(taskWrappers[0]);

      // task 3 inserts before task 1: [3, 1, 2]
      expect(mockSimulationEngine.reorderTasks).toHaveBeenCalledWith(
        1,
        [3, 1, 2],
        true
      );
    });

    it('should start drag select on right-click (mousedown button=2) on a driver task', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      // This test is intended to act on the expanded task view
      const collapseToggle = screen.getByRole('button', {
        name: 'Expand task list',
      });
      fireEvent.click(collapseToggle);

      const taskItems = screen.getAllByText(/^#/);
      const firstWrapper = taskItems[0].closest('[data-slot="item"]')!
        .parentElement as HTMLElement;

      fireEvent.mouseDown(firstWrapper, { button: 2 });

      // After right-click drag start, task 1 should be selected
      expect(screen.getByText('Tasks (1/3 selected)')).toBeInTheDocument();
    });

    it('should call requestUnassignment when driver task unassign is clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 3,
                  name: 'Driver 3',
                  tasks: [makeStationTask({ id: 10, assignedDriverId: 3 })],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      const unassignButton = screen
        .getAllByRole('button')
        .find((btn) => btn.closest('[data-slot="item"]') !== null);
      expect(unassignButton).toBeDefined();
      await user.click(unassignButton!);

      expect(mockSimulationEngine.requestUnassignment).toHaveBeenCalledWith(
        3,
        10
      );
    });

    it('should reset drag state on dragEnd', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      const taskElements = screen
        .getAllByText(/^#/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];

      // Start drag on task 1
      fireEvent.dragStart(taskElements[0]);

      // Re-query after dragStart re-render (state updates make old refs stale)
      const freshWrappers1 = screen
        .getAllByText(/^#/)
        .map(
          (el) => el.closest('[data-slot="item"]')!.parentElement as HTMLElement
        );

      // Drag over task 3 to set dropTargetIndex
      fireEvent.dragOver(freshWrappers1[2], {
        dataTransfer: { dropEffect: '' },
      });

      // Re-query after dragOver re-render
      const freshWrappers2 = screen
        .getAllByText(/^#/)
        .map(
          (el) => el.closest('[data-slot="item"]')!.parentElement as HTMLElement
        );
      expect(freshWrappers2[2].className).toContain('border-b-2');

      // End drag — should reset the drop indicator
      fireEvent.dragEnd(freshWrappers2[0]);

      // Re-query after dragEnd re-render
      const freshWrappers3 = screen
        .getAllByText(/^#/)
        .map(
          (el) => el.closest('[data-slot="item"]')!.parentElement as HTMLElement
        );
      freshWrappers3.forEach((wrapper) => {
        expect(wrapper.className).not.toContain('border-b-2');
        expect(wrapper.className).not.toContain('border-t-2');
      });
    });

    it('should show drop indicator above when dragging up', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                    makeStationTask({ id: 3 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      const taskElements = screen
        .getAllByText(/^#/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];

      // Start drag on task 3 (index 2)
      fireEvent.dragStart(taskElements[2]);

      // Re-query after dragStart re-render
      const freshWrappers = screen
        .getAllByText(/^#/)
        .map(
          (el) => el.closest('[data-slot="item"]')!.parentElement as HTMLElement
        );

      // Drag over task 1 (index 0) — dragging upward
      fireEvent.dragOver(freshWrappers[0], {
        dataTransfer: { dropEffect: '' },
      });

      // Re-query after dragOver re-render
      const freshWrappers2 = screen
        .getAllByText(/^#/)
        .map(
          (el) => el.closest('[data-slot="item"]')!.parentElement as HTMLElement
        );
      // Should show top border indicator (dragging up)
      expect(freshWrappers2[0].className).toContain('border-t-2');
    });

    it('should not reorder when drop occurs at same position', () => {
      vi.mocked(useSimulation).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({
                  id: 1,
                  name: 'Driver 1',
                  tasks: [
                    makeStationTask({ id: 1 }),
                    makeStationTask({ id: 2 }),
                  ],
                }),
              }),
            ],
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      fireEvent.click(screen.getByRole('button', { name: 'Expand task list' }));

      const taskElements = screen
        .getAllByText(/^#/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Drag task 1 and drop on itself (index 0 → index 0)
      fireEvent.dragStart(taskElements[0]);
      fireEvent.drop(taskWrappers[0]);

      // Should not reorder since source === target
      expect(mockSimulationEngine.reorderTasks).not.toHaveBeenCalled();
    });
  });
});
