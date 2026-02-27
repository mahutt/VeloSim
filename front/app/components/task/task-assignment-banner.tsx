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

import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { useSimulation } from '~/providers/simulation-provider';
import { TaskAction, type ReassignTaskAction } from '~/types';

export function TaskAssignmentBanner() {
  const { state, engine } = useSimulation();
  const { pendingAssignment, pendingAssignmentLoading: isLoading } = state;

  const [loadingAction, setLoadingAction] = useState<
    'all' | 'remaining' | null
  >(null);
  if (!pendingAssignment) return null;

  const taskIds = pendingAssignment.taskIds;
  const count = taskIds.length;
  const isMulti = count > 1;
  const firstTaskId = taskIds[0];

  // When action is 'assign' but every task belongs to another driver,
  // the user is really doing a reassign (from multiple sources).
  const action = pendingAssignment.action;
  const reassignCount =
    pendingAssignment.action === TaskAction.Assign
      ? pendingAssignment.reassignCount
      : 0;
  const isAllReassign =
    action === TaskAction.Assign && isMulti && reassignCount === count;

  // Mixed = some assigned, some not → show 3-button UI
  const hasMixedTasks =
    action === TaskAction.Assign &&
    isMulti &&
    reassignCount > 0 &&
    reassignCount < count;

  const unassignedCount = count - reassignCount;

  // Derive a display label from the action + reassign state
  const actionLabel =
    isAllReassign || action === TaskAction.Reassign ? 'Re-assign' : 'Assign';

  const exceedsBattery =
    count > pendingAssignment.driverBatteryCount &&
    (action === TaskAction.Assign || action === TaskAction.Reassign);

  const driverName = pendingAssignment.driverName;
  const remainingBatteryCount = pendingAssignment.driverBatteryCount;
  const prevDriverName =
    (pendingAssignment as ReassignTaskAction).prevDriverName ?? undefined;

  const renderMessage = () => {
    if (!count) return null;

    // Battery warning (assign / reassign only)
    if (exceedsBattery) {
      return (
        <>
          <span className="block">
            {driverName} has {remainingBatteryCount}{' '}
            {remainingBatteryCount === 1 ? 'battery' : 'batteries'} remaining.
          </span>
          <span className="block">
            {actionLabel} {count} {count === 1 ? 'task' : 'tasks'} anyway?
          </span>
          {hasMixedTasks && (
            <span className="block text-muted-foreground">
              ({reassignCount} {reassignCount === 1 ? 'task' : 'tasks'} already
              assigned to other drivers)
            </span>
          )}
        </>
      );
    }

    // Unassign
    if (action === TaskAction.Unassign) {
      return `Un-assign task #${firstTaskId} from ${driverName}?`;
    }

    // Reassign from a single known driver
    if (action === TaskAction.Reassign && prevDriverName !== undefined) {
      return isMulti
        ? `Re-assign ${count} tasks from ${prevDriverName} to ${driverName}?`
        : `Re-assign task #${firstTaskId} from ${prevDriverName} to ${driverName}?`;
    }

    // All tasks already assigned (multiple source drivers)
    if (isAllReassign) {
      return `Re-assign ${count} tasks to ${driverName}?`;
    }

    // Mixed batch (some assigned, some not)
    if (hasMixedTasks) {
      return (
        <>
          <span className="block">
            Assign {count} tasks to {driverName}?
          </span>
          <span className="block text-muted-foreground">
            ({reassignCount} {reassignCount === 1 ? 'task' : 'tasks'} already
            assigned to other drivers)
          </span>
        </>
      );
    }

    // Pure assign
    return isMulti
      ? `Assign ${count} tasks to ${driverName}?`
      : `Assign task #${firstTaskId} to ${driverName}?`;
  };

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50">
      <div className="bg-white border rounded-lg shadow-lg p-4">
        <div className="flex items-center gap-2 mb-3 justify-center">
          <AlertCircle className="h-5 w-5 text-amber-500" />
          <div className="text-sm">{renderMessage()}</div>
        </div>
        <div className="flex gap-2 justify-center">
          <Button
            onClick={() => engine.cancelAssignment()}
            size="sm"
            variant="outline"
            disabled={isLoading}
            aria-busy={isLoading}
          >
            Cancel
          </Button>
          {hasMixedTasks ? (
            <>
              <Button
                onClick={() => {
                  setLoadingAction('remaining');
                  engine.confirmAssignment(true);
                }}
                size="sm"
                disabled={isLoading}
                aria-busy={isLoading && loadingAction === 'remaining'}
                className="bg-blue-500 hover:bg-blue-400 text-white"
              >
                {isLoading && loadingAction === 'remaining'
                  ? 'Assigning...'
                  : `Remaining (${unassignedCount})`}
              </Button>
              <Button
                onClick={() => {
                  setLoadingAction('all');
                  engine.confirmAssignment();
                }}
                size="sm"
                disabled={isLoading}
                aria-busy={isLoading && loadingAction === 'all'}
              >
                {isLoading && loadingAction === 'all'
                  ? 'Assigning...'
                  : `All (${taskIds.length})`}
              </Button>
            </>
          ) : (
            <Button
              onClick={() => engine.confirmAssignment()}
              size="sm"
              disabled={isLoading}
              aria-busy={isLoading}
            >
              {isLoading ? 'Confirming...' : 'Confirm'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
