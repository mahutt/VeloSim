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
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { TaskAssignmentBanner } from '~/components/task/task-assignment-banner';

describe('TaskAssignmentBanner', () => {
  it('renders prompt with task and resource name and buttons', () => {
    render(
      <TaskAssignmentBanner
        taskIds={[1]}
        driverName="Driver A"
        remainingBatteryCount={10}
        action="assign"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    );

    expect(
      screen.getByText(/Assign task #1 to Driver A\?/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /confirm/i })
    ).toBeInTheDocument();
  });

  it('calls onConfirm and onCancel when buttons are clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    render(
      <TaskAssignmentBanner
        taskIds={[1]}
        driverName="Driver B"
        remainingBatteryCount={10}
        action="assign"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    await user.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('renders reassign prompt when action is reassign and previous resource is provided', () => {
    render(
      <TaskAssignmentBanner
        taskIds={[1]}
        driverName="Driver B"
        prevDriverName="Driver A"
        remainingBatteryCount={10}
        action="reassign"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    );

    expect(
      screen.getByText(/Re-assign task #1 from Driver A to Driver B\?/i)
    ).toBeInTheDocument();
  });

  it('renders unassign prompt when action is unassign', () => {
    render(
      <TaskAssignmentBanner
        taskIds={[5]}
        driverName="Driver C"
        remainingBatteryCount={10}
        action="unassign"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    );

    expect(
      screen.getByText(/Un-assign task #5 from Driver C\?/i)
    ).toBeInTheDocument();
  });

  it('shows three buttons when batch assign has mixed tasks', () => {
    render(
      <TaskAssignmentBanner
        taskIds={[1, 2, 3, 4, 5]}
        driverName="Driver A"
        remainingBatteryCount={10}
        action="assign"
        reassignCount={2}
        onConfirm={() => {}}
        onConfirmUnassignedOnly={() => {}}
        onCancel={() => {}}
      />
    );

    expect(
      screen.getByText(/Assign 5 tasks to Driver A\?/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/2 already assigned to other drivers/i)
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
    const onConfirmUnassignedOnly = vi.fn();

    render(
      <TaskAssignmentBanner
        taskIds={[1, 2, 3]}
        driverName="Driver A"
        remainingBatteryCount={10}
        action="assign"
        reassignCount={1}
        onConfirm={() => {}}
        onConfirmUnassignedOnly={onConfirmUnassignedOnly}
        onCancel={() => {}}
      />
    );

    await user.click(screen.getByRole('button', { name: /remaining \(2\)/i }));
    expect(onConfirmUnassignedOnly).toHaveBeenCalledTimes(1);
  });

  it('shows single confirm button when no tasks are reassigned', () => {
    render(
      <TaskAssignmentBanner
        taskIds={[1, 2, 3]}
        driverName="Driver A"
        remainingBatteryCount={10}
        action="assign"
        reassignCount={0}
        onConfirm={() => {}}
        onConfirmUnassignedOnly={() => {}}
        onCancel={() => {}}
      />
    );

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /confirm/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /remaining/i })
    ).not.toBeInTheDocument();
  });
});
