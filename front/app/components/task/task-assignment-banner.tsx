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
import type { TaskAction } from '~/types';

interface TaskAssignmentBannerProps {
  taskIds: number[];
  driverName: string;
  prevDriverName?: string;
  remainingBatteryCount: number;
  action: TaskAction;
  reassignCount?: number;
  isLoading?: boolean;
  onConfirm: () => void;
  onConfirmUnassignedOnly?: () => void;
  onCancel: () => void;
}

export function TaskAssignmentBanner({
  taskIds,
  driverName,
  prevDriverName,
  remainingBatteryCount,
  action,
  reassignCount = 0,
  isLoading = false,
  onConfirm,
  onConfirmUnassignedOnly,
  onCancel,
}: TaskAssignmentBannerProps) {
  const [loadingAction, setLoadingAction] = useState<
    'all' | 'remaining' | null
  >(null);
  const hasMixedTasks =
    action === 'assign' &&
    taskIds.length > 1 &&
    reassignCount > 0 &&
    reassignCount < taskIds.length;
  const unassignedCount = taskIds.length - reassignCount;

  const renderMessage = () => {
    if (!taskIds.length) return null;

    const firstTaskId = taskIds[0];
    const exceedsBattery =
      taskIds.length > remainingBatteryCount &&
      (action === 'assign' || action === 'reassign');

    if (exceedsBattery) {
      const actionLabel = action === 'reassign' ? 'Re-assign' : 'Assign';

      return (
        <>
          <span className="block">
            {driverName} has {remainingBatteryCount}{' '}
            {remainingBatteryCount === 1 ? 'battery' : 'batteries'} remaining.
          </span>
          {hasMixedTasks && (
            <span className="block text-muted-foreground">
              ({reassignCount} already assigned to other drivers)
            </span>
          )}
          <span className="block">
            {actionLabel} {taskIds.length}{' '}
            {taskIds.length === 1 ? 'task' : 'tasks'} anyway?
          </span>
        </>
      );
    }

    if (action === 'reassign' && prevDriverName !== undefined) {
      if (taskIds.length > 1) {
        return `Re-assign ${taskIds.length} tasks from ${prevDriverName} to ${driverName}?`;
      }
      return `Re-assign task #${firstTaskId} from ${prevDriverName} to ${driverName}?`;
    }
    if (action === 'unassign') {
      return `Un-assign task #${firstTaskId} from ${driverName}?`;
    }
    if (action === 'assign') {
      if (hasMixedTasks) {
        return (
          <>
            <span className="block">
              Assign {taskIds.length} tasks to {driverName}?
            </span>
            <span className="block">
              ({reassignCount} already assigned to other drivers)
            </span>
          </>
        );
      }
      if (taskIds.length > 1) {
        return `Assign ${taskIds.length} tasks to ${driverName}?`;
      }
      return `Assign task #${firstTaskId} to ${driverName}?`;
    }
    return null;
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
            onClick={onCancel}
            size="sm"
            variant="outline"
            disabled={isLoading}
            aria-busy={isLoading}
          >
            Cancel
          </Button>
          {hasMixedTasks && onConfirmUnassignedOnly ? (
            <>
              <Button
                onClick={() => {
                  setLoadingAction('remaining');
                  onConfirmUnassignedOnly();
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
                  onConfirm();
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
              onClick={onConfirm}
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
