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

import { AlertCircle } from 'lucide-react';
import { Button } from '~/components/ui/button';
import type { TaskAction } from '~/types';

interface TaskAssignmentBannerProps {
  taskIds: number[];
  resourceId: number;
  prevResourceId?: number;
  action: TaskAction;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function TaskAssignmentBanner({
  taskIds,
  resourceId,
  prevResourceId,
  action,
  isLoading = false,
  onConfirm,
  onCancel,
}: TaskAssignmentBannerProps) {
  const renderMessage = () => {
    if (!taskIds.length) return null;

    const firstTaskId = taskIds[0];

    if (action === 'reassign' && prevResourceId !== undefined) {
      if (taskIds.length > 1) {
        return `Re-assign ${taskIds.length} tasks from resource #${prevResourceId} to resource #${resourceId}?`;
      }
      return `Re-assign task #${firstTaskId} from resource #${prevResourceId} to resource #${resourceId}?`;
    }
    if (action === 'unassign') {
      return `Un-assign task #${firstTaskId} from resource #${resourceId}?`;
    }
    if (action === 'assign') {
      if (taskIds.length > 1) {
        return `Assign ${taskIds.length} tasks to resource #${resourceId}?`;
      }
      return `Assign task #${firstTaskId} to resource #${resourceId}?`;
    }
    return null;
  };

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50">
      <div className="bg-white border rounded-lg shadow-lg p-4">
        <div className="flex items-center gap-2 mb-3 justify-center">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">{renderMessage()}</span>
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
          <Button
            onClick={onConfirm}
            size="sm"
            disabled={isLoading}
            aria-busy={isLoading}
          >
            {isLoading ? 'Confirming...' : 'Confirm'}
          </Button>
        </div>
      </div>
    </div>
  );
}
