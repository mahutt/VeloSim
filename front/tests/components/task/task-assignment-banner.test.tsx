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
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { TaskAssignmentBanner } from '~/components/task/task-assignment-banner';
import {
  useSimulation,
  type SimulationContextType,
} from '~/providers/simulation-provider';
import type SimulationEngine from '~/lib/simulation-engine';
import { makePendingAssignment } from 'tests/test-helpers';
import { TaskAction } from '~/types';

const { mockUseSimulation } = await vi.hoisted(async () => {
  const { mockSimulationEngine } = await import('tests/mocks');
  const { DEFAULT_REACTIVE_SIMULATION_STATE } =
    await import('app/lib/reactive-simulation-state');
  const mockUseSimulationResult: SimulationContextType = {
    state: DEFAULT_REACTIVE_SIMULATION_STATE,
    engine: mockSimulationEngine as SimulationEngine,
  };
  const mockUseSimulation = () => mockUseSimulationResult;
  return { mockUseSimulation };
});

vi.mock(import('~/providers/simulation-provider'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useSimulation: mockUseSimulation,
  };
});

describe('TaskAssignmentBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it('calls onConfirm and onCancel when buttons are clicked', async () => {
    useSimulation().state.pendingAssignment = makePendingAssignment();
    const user = userEvent.setup();

    render(<TaskAssignmentBanner />);

    await user.click(screen.getByRole('button', { name: /confirm/i }));
    expect(useSimulation().engine.confirmAssignment).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(useSimulation().engine.cancelAssignment).toHaveBeenCalledTimes(1);
  });

  it('renders reassign prompt when action is reassign and previous resource is provided', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Reassign,
      taskIds: [1],
      driverId: 1,
      driverName: 'Driver B',
      driverBatteryCount: 3,
      prevDriverId: 2,
      prevDriverName: 'Driver A',
    });
    render(<TaskAssignmentBanner />);

    expect(
      screen.getByText(/Re-assign task #1 from Driver A to Driver B\?/i)
    ).toBeInTheDocument();
  });

  it('renders unassign prompt when action is unassign', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Unassign,
      taskIds: [5],
      driverId: 3,
      driverName: 'Driver C',
    });
    render(<TaskAssignmentBanner />);

    expect(
      screen.getByText(/Un-assign task #5 from Driver C\?/i)
    ).toBeInTheDocument();
  });

  it('notifies user when there are more tasks being assigned than batteries left', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Assign,
      taskIds: [5],
      driverId: 3,
      driverName: 'Driver 3',
      driverBatteryCount: 0,
    });
    render(<TaskAssignmentBanner />);

    expect(
      screen.getByText(/Driver 3 has 0 batteries remaining\./i)
    ).toBeInTheDocument();
  });

  it('shows three buttons when batch assign has mixed tasks', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Assign,
      taskIds: [1, 2, 3, 4, 5],
      driverId: 3,
      driverName: 'Driver A',
      driverBatteryCount: 10,
      reassignCount: 2,
    });
    render(<TaskAssignmentBanner />);

    expect(
      screen.getByText(/Assign 5 tasks to Driver A\?/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/2 tasks already assigned to other drivers/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /remaining \(3\)/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /all \(5\)/i })
    ).toBeInTheDocument();
  });

  it('calls onConfirmUnassignedOnly when assign unassigned only is clicked', async () => {
    const user = userEvent.setup();

    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Assign,
      taskIds: [1, 2, 3],
      driverId: 3,
      driverName: 'Driver A',
      driverBatteryCount: 10,
      reassignCount: 1,
    });
    render(<TaskAssignmentBanner />);

    await user.click(screen.getByRole('button', { name: /remaining \(2\)/i }));
    expect(useSimulation().engine.confirmUnassignedOnly).toHaveBeenCalledTimes(
      1
    );
  });

  it('shows single confirm button when no tasks are reassigned', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Assign,
      taskIds: [1, 2, 3],
      driverId: 3,
      driverName: 'Driver A',
      driverBatteryCount: 10,
      reassignCount: 0,
    });
    render(<TaskAssignmentBanner />);

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /confirm/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /remaining/i })
    ).not.toBeInTheDocument();
  });

  it('shows reassign message when all tasks are already assigned to other drivers', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Assign,
      taskIds: [1, 2],
      driverId: 3,
      driverName: 'Driver C',
      driverBatteryCount: 10,
      reassignCount: 2,
    });
    render(<TaskAssignmentBanner />);

    expect(
      screen.getByText(/Re-assign 2 tasks to Driver C\?/i)
    ).toBeInTheDocument();
    // Should show single confirm, not the 3-button mixed UI
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /confirm/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /remaining/i })
    ).not.toBeInTheDocument();
  });

  it('renders multi-reassign prompt from a single known driver', () => {
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Reassign,
      taskIds: [1, 2, 3],
      driverId: 3,
      driverName: 'Driver B',
      driverBatteryCount: 10,
      prevDriverId: 2,
      prevDriverName: 'Driver A',
    });
    render(<TaskAssignmentBanner />);

    expect(
      screen.getByText(/Re-assign 3 tasks from Driver A to Driver B\?/i)
    ).toBeInTheDocument();
  });

  it('shows loading text on mixed-task Remaining button when isLoading', async () => {
    const user = userEvent.setup();
    useSimulation().state.pendingAssignment = makePendingAssignment({
      action: TaskAction.Assign,
      taskIds: [1, 2, 3],
      driverId: 3,
      driverName: 'Driver A',
      driverBatteryCount: 10,
      reassignCount: 1,
    });
    useSimulation().state.pendingAssignmentLoading = false;

    render(<TaskAssignmentBanner />);

    await user.click(screen.getByRole('button', { name: /remaining \(2\)/i }));
    expect(useSimulation().engine.confirmUnassignedOnly).toHaveBeenCalledTimes(
      1
    );
  });
});
