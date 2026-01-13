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
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import {
  TaskAssignmentProvider,
  useTaskAssignment,
} from '~/providers/task-assignment-provider';
import { useSimulation } from '~/providers/simulation-provider';
import type { Driver } from '~/types';
import { makeDriver } from 'tests/test-helpers';

vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

function TestComponent() {
  const {
    pendingAssignment,
    requestAssignment,
    requestUnassignment,
    confirmAssignment,
  } = useTaskAssignment();

  return (
    <div>
      <button
        data-testid="req-assign"
        onClick={() => requestAssignment(10, 42)}
      >
        Request Assign
      </button>
      <button
        data-testid="req-unassign"
        onClick={() => requestUnassignment(5, 99)}
      >
        Request Unassign
      </button>
      <button data-testid="confirm" onClick={() => confirmAssignment()}>
        Confirm
      </button>
      <div data-testid="pending">{pendingAssignment?.action ?? 'none'}</div>
      <div data-testid="prev">
        {pendingAssignment?.action === 'reassign'
          ? String(pendingAssignment.prevResourceId)
          : 'none'}
      </div>
    </div>
  );
}

describe('TaskAssignmentProvider', () => {
  it('creates an assign pending assignment and calls assignTask on confirm', async () => {
    const assignTask = vi.fn();
    const unassignTask = vi.fn();
    const reassignTask = vi.fn();

    // driversRef has no assignment for task 42
    const driversRef = { current: new Map<number, unknown>() };

    vi.mocked(useSimulation).mockReturnValue({
      assignTask,
      unassignTask,
      reassignTask,
      driversRef,
    } as unknown as ReturnType<typeof useSimulation>);

    const user = userEvent.setup();

    render(
      <TaskAssignmentProvider>
        <TestComponent />
      </TaskAssignmentProvider>
    );

    await user.click(screen.getByTestId('req-assign'));
    expect(screen.getByTestId('pending').textContent).toBe('assign');

    await user.click(screen.getByTestId('confirm'));

    await waitFor(() => {
      expect(assignTask).toHaveBeenCalledWith(10, 42);
    });
  });

  it('creates a reassign pending assignment when task already assigned and calls reassignTask on confirm', async () => {
    const assignTask = vi.fn();
    const unassignTask = vi.fn();
    const reassignTask = vi.fn();

    // driversRef contains resource 5 that already has task 42
    const driversRef = {
      current: new Map<number, Driver>([
        [5, makeDriver({ id: 5, taskIds: [42] })],
      ]),
    };

    vi.mocked(useSimulation).mockReturnValue({
      assignTask,
      unassignTask,
      reassignTask,
      driversRef,
    } as unknown as ReturnType<typeof useSimulation>);

    const user = userEvent.setup();

    render(
      <TaskAssignmentProvider>
        <TestComponent />
      </TaskAssignmentProvider>
    );

    await user.click(screen.getByTestId('req-assign'));

    // Should detect previous resource and set action to reassign
    expect(screen.getByTestId('pending').textContent).toBe('reassign');
    expect(screen.getByTestId('prev').textContent).toBe('5');

    await user.click(screen.getByTestId('confirm'));

    await waitFor(() => {
      expect(reassignTask).toHaveBeenCalledWith(5, 10, 42);
    });
  });

  it('creates an unassign pending assignment and calls unassignTask on confirm', async () => {
    const assignTask = vi.fn();
    const unassignTask = vi.fn();
    const reassignTask = vi.fn();

    const driversRef = { current: new Map<number, unknown>() };

    vi.mocked(useSimulation).mockReturnValue({
      assignTask,
      unassignTask,
      reassignTask,
      driversRef,
    } as unknown as ReturnType<typeof useSimulation>);

    const user = userEvent.setup();

    render(
      <TaskAssignmentProvider>
        <TestComponent />
      </TaskAssignmentProvider>
    );

    await user.click(screen.getByTestId('req-unassign'));
    expect(screen.getByTestId('pending').textContent).toBe('unassign');

    await user.click(screen.getByTestId('confirm'));

    await waitFor(() => {
      expect(unassignTask).toHaveBeenCalledWith(5, 99);
    });
  });
});
