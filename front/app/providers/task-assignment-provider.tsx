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

type PendingAssignment = { taskId: number; resourceId: number } | null;

type TaskAssignmentContextType = {
  pendingAssignment: PendingAssignment;
  requestAssignment: (resourceId: number, taskId: number) => void;
  confirmAssignment: () => Promise<void>;
  cancelAssignment: () => void;
};

const TaskAssignmentContext = createContext<
  TaskAssignmentContextType | undefined
>(undefined);

export function TaskAssignmentProvider({ children }: { children: ReactNode }) {
  const { assignTaskToResource } = useSimulation();
  const [pendingAssignment, setPendingAssignment] =
    useState<PendingAssignment>(null);

  const requestAssignment = useCallback(
    (resourceId: number, taskId: number) => {
      setPendingAssignment({ taskId, resourceId });
    },
    []
  );

  const confirmAssignment = useCallback(async () => {
    if (pendingAssignment) {
      try {
        await assignTaskToResource(
          pendingAssignment.resourceId,
          pendingAssignment.taskId
        );
      } catch (error) {
        console.error('Failed to assign task to resource:', error);
      } finally {
        setPendingAssignment(null);
      }
    }
  }, [pendingAssignment, assignTaskToResource]);

  const cancelAssignment = useCallback(() => {
    setPendingAssignment(null);
  }, []);

  return (
    <TaskAssignmentContext.Provider
      value={{
        pendingAssignment,
        requestAssignment,
        confirmAssignment,
        cancelAssignment,
      }}
    >
      {pendingAssignment && (
        <TaskAssignmentBanner
          taskId={pendingAssignment.taskId}
          resourceId={pendingAssignment.resourceId}
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
