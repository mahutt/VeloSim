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

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react';
import { TaskAssignmentBanner } from '~/components/task/task-assignment-banner';
import { useSimulation } from './simulation-provider';

type PendingAssignment =
  | {
      action: 'assign';
      taskId: number;
      resourceId: number;
    }
  | {
      action: 'reassign';
      taskId: number;
      resourceId: number;
      prevResourceId: number;
    }
  | {
      action: 'unassign';
      taskId: number;
      resourceId: number;
    }
  | null;

type TaskAssignmentContextType = {
  pendingAssignment: PendingAssignment;
  requestAssignment: (resourceId: number, taskId: number) => void;
  requestReassignment: (
    previousResourceId: number,
    newResourceId: number,
    taskId: number
  ) => void;
  requestUnassignment: (resourceId: number, taskId: number) => void;
  confirmAssignment: () => Promise<void>;
  cancelAssignment: () => void;
};

const TaskAssignmentContext = createContext<
  TaskAssignmentContextType | undefined
>(undefined);

export function TaskAssignmentProvider({ children }: { children: ReactNode }) {
  const { assignTask, unassignTask, reassignTask, driversRef } =
    useSimulation();
  const [pendingAssignment, setPendingAssignment] =
    useState<PendingAssignment>(null);

  const requestReassignment = useCallback(
    (prevResourceId: number, resourceId: number, taskId: number) => {
      setPendingAssignment({
        taskId,
        resourceId,
        prevResourceId,
        action: 'reassign',
      });
    },
    []
  );

  const requestAssignment = useCallback(
    (resourceId: number, taskId: number) => {
      const assignedResource = Array.from(driversRef.current.values()).find(
        (r) => r.taskIds && r.taskIds.includes(taskId)
      );

      if (assignedResource) {
        if (assignedResource.id === resourceId) {
          return;
        }

        requestReassignment(assignedResource.id, resourceId, taskId);
        return;
      }

      setPendingAssignment({ taskId, resourceId, action: 'assign' });
    },
    [driversRef, requestReassignment]
  );

  const requestUnassignment = useCallback(
    (resourceId: number, taskId: number) => {
      setPendingAssignment({ taskId, resourceId, action: 'unassign' });
    },
    []
  );

  const confirmAssignment = useCallback(async () => {
    if (!pendingAssignment) return;

    try {
      if (pendingAssignment.action === 'unassign') {
        await unassignTask(
          pendingAssignment.resourceId,
          pendingAssignment.taskId
        );
      } else if (pendingAssignment.action === 'reassign') {
        await reassignTask(
          pendingAssignment.prevResourceId,
          pendingAssignment.resourceId,
          pendingAssignment.taskId
        );
      } else {
        await assignTask(
          pendingAssignment.resourceId,
          pendingAssignment.taskId
        );
      }
    } catch (error) {
      console.error('Failed to complete task assignment action:', error);
    } finally {
      setPendingAssignment(null);
    }
  }, [pendingAssignment, assignTask, unassignTask, reassignTask]);

  const cancelAssignment = useCallback(() => {
    setPendingAssignment(null);
  }, []);

  return (
    <TaskAssignmentContext.Provider
      value={{
        pendingAssignment,
        requestAssignment,
        requestReassignment,
        requestUnassignment,
        confirmAssignment,
        cancelAssignment,
      }}
    >
      {pendingAssignment && (
        <TaskAssignmentBanner
          taskId={pendingAssignment.taskId}
          resourceId={pendingAssignment.resourceId}
          prevResourceId={
            pendingAssignment.action === 'reassign'
              ? pendingAssignment.prevResourceId
              : undefined
          }
          action={pendingAssignment.action}
          onConfirm={confirmAssignment}
          onCancel={cancelAssignment}
        />
      )}
      {children}
    </TaskAssignmentContext.Provider>
  );
}

export function useTaskAssignment() {
  const ctx = useContext(TaskAssignmentContext);
  if (!ctx) {
    throw new Error(
      'useTaskAssignment must be used within TaskAssignmentProvider'
    );
  }
  return ctx;
}
