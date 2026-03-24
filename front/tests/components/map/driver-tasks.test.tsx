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
});
