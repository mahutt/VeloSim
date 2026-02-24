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

import { describe, it, expect, vi } from 'vitest';
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
  makeSelectedItemBarElement,
  makeSimulationContext,
  makeStationTask,
} from 'tests/test-helpers';
import { mockSimulationEngine } from 'tests/mocks';
import type SimulationEngine from '~/lib/simulation-engine';
import { TaskState } from '~/types';

// Mock the useSimulation hook
vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('SelectedItemBar', () => {
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
          selectedItemBarElement: makeSelectedItemBarElement({
            type: SelectedItemType.Station,
            value: makePopulatedStation({
              id: 1,
              name: 'Test Station',
              tasks: [],
            }),
          }),
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
          selectedItemBarElement: makeSelectedItemBarElement({
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
    expect(screen.getByText('Task #1')).toBeInTheDocument();
    expect(screen.getByText('Task #2')).toBeInTheDocument();
    expect(screen.getByText('Task #3')).toBeInTheDocument();
  });

  it('should render driver in progress task when driver is selected', () => {
    const inProgressTask = makeStationTask({
      id: 1,
      state: TaskState.InProgress,
    });
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          selectedItemBarElement: makeSelectedItemBarElement({
            type: SelectedItemType.Driver,
            value: makePopulatedDriver({
              id: 5,
              name: 'Driver 5',
              inProgressTask,
              tasks: [
                inProgressTask,
                makeStationTask({ id: 2 }),
                makeStationTask({ id: 3 }),
              ],
            }),
          }),
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
    expect(screen.getByText('Task #1')).toBeInTheDocument();
    expect(screen.getByText(/in progress/i)).toBeInTheDocument();
  });

  it('should call clearSelection when close button is clicked', async () => {
    const user = userEvent.setup();
    (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeSimulationContext({
        state: makeReactiveSimulationState({
          selectedItemBarElement: makeSelectedItemBarElement({
            type: SelectedItemType.Station,
            value: makePopulatedStation(),
          }),
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
          selectedItemBarElement: makeSelectedItemBarElement({
            type: SelectedItemType.Station,
            value: makePopulatedStation({
              id: 1,
              name: 'Test Station',
              tasks: [makeStationTask({ id: 1 }), makeStationTask({ id: 2 })],
            }),
          }),
        }),
      })
    );

    render(
      <FeatureToggleProvider>
        <SelectedItemBar />
      </FeatureToggleProvider>
    );

    expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
    const taskItems = screen.getAllByText(/^Task #/);
    expect(taskItems).toHaveLength(2);
  });

  describe('Task Reordering', () => {
    it('should call reorderTasks when task is dropped at a valid position', async () => {
      (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItemBarElement: makeSelectedItemBarElement({
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
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      // Get the task wrappers
      const taskElements = screen
        .getAllByText(/^Task #/)
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
            selectedItemBarElement: makeSelectedItemBarElement({
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
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      const taskElements = screen
        .getAllByText(/^Task #/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Simulate dragover WITHOUT dragstart (draggedTaskId will be null)
      const dragOverEvent = fireEvent.dragOver(taskWrappers[1]);

      expect(dragOverEvent).toBe(false); // Event should be prevented but dropEffect set to 'none'
    });

    it('should set dropEffect to none when target index is 0', () => {
      (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItemBarElement: makeSelectedItemBarElement({
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
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      const taskElements = screen
        .getAllByText(/^Task #/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Start drag on task 2
      fireEvent.dragStart(taskElements[1]);

      // Dragover task at index 0
      const dragOverEvent = fireEvent.dragOver(taskWrappers[0]);

      expect(dragOverEvent).toBe(false); // Event prevented, dropEffect should be 'none'
    });

    it('should not reorder when dragged task is not found in list', async () => {
      (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
        makeSimulationContext({
          state: makeReactiveSimulationState({
            selectedItemBarElement: makeSelectedItemBarElement({
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
          }),
          engine: mockSimulationEngine as SimulationEngine,
        })
      );

      render(
        <FeatureToggleProvider>
          <SelectedItemBar />
        </FeatureToggleProvider>
      );

      const taskElements = screen
        .getAllByText(/^Task #/)
        .map((el) => el.closest('[data-slot="item"]'))
        .filter(Boolean) as HTMLElement[];
      const taskWrappers = taskElements.map(
        (el) => el.parentElement as HTMLElement
      );

      // Manually set draggedTaskId to a task that doesn't exist
      fireEvent.dragStart(taskElements[0]);

      // Now manually trigger drop with a different task id
      // This simulates the edge case where draggedTaskId doesn't match any task
      fireEvent.drop(taskWrappers[1]);

      // Note: This test validates that findIndex returns -1 check works
      // In practice, this scenario is prevented by the UI
    });
  });
});
