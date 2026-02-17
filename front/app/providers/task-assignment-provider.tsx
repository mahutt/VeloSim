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
      taskIds: number[];
      unassignedTaskIds: number[];
      resourceId: number;
      reassignCount: number;
    }
  | {
      action: 'reassign';
      taskIds: number[];
      resourceId: number;
      prevResourceId: number;
    }
  | {
      action: 'unassign';
      taskIds: number[];
      resourceId: number;
    }
  | null;

type TaskAssignmentContextType = {
  pendingAssignment: PendingAssignment;
  isLoading: boolean;
  requestAssignment: (resourceId: number, taskIds: number[]) => void;
  requestReassignment: (
    previousResourceId: number,
    newResourceId: number,
    taskId: number
  ) => void;
  requestUnassignment: (resourceId: number, taskId: number) => void;
  confirmAssignment: () => Promise<void>;
  confirmUnassignedOnly: () => Promise<void>;
  cancelAssignment: () => void;
};

const TaskAssignmentContext = createContext<
  TaskAssignmentContextType | undefined
>(undefined);

export function TaskAssignmentProvider({ children }: { children: ReactNode }) {
  const {
    assignTask,
    assignTasksBatch,
    unassignTask,
    reassignTask,
    driversRef,
    vehiclesRef,
  } = useSimulation();
  const [pendingAssignment, setPendingAssignment] =
    useState<PendingAssignment>(null);
  const [isLoading, setIsLoading] = useState(false);

  const requestReassignment = useCallback(
    (prevResourceId: number, resourceId: number, taskId: number) => {
      setPendingAssignment({
        taskIds: [taskId],
        resourceId,
        prevResourceId,
        action: 'reassign',
      });
    },
    []
  );

  const requestAssignment = useCallback(
    (resourceId: number, taskIds: number[]) => {
      if (taskIds.length === 0) return;

      const drivers = Array.from(driversRef.current.values());

      if (taskIds.length > 1) {
        let prevResourceId: number | null = null;
        let sameResourceAssigned = true;

        for (const taskId of taskIds) {
          const assignedResource = drivers.find(
            (r) => r.taskIds && r.taskIds.includes(taskId)
          );

          if (!assignedResource) {
            sameResourceAssigned = false;
            break;
          }

          if (prevResourceId === null) {
            prevResourceId = assignedResource.id;
          } else if (assignedResource.id !== prevResourceId) {
            sameResourceAssigned = false;
            break;
          }
        }

        if (sameResourceAssigned && prevResourceId !== null) {
          if (prevResourceId === resourceId) {
            return;
          }
          setPendingAssignment({
            taskIds,
            resourceId,
            prevResourceId,
            action: 'reassign',
          });
          return;
        }

        const reassignCount = taskIds.filter((taskId) => {
          return drivers.some(
            (r) =>
              r.id !== resourceId && r.taskIds && r.taskIds.includes(taskId)
          );
        }).length;

        const unassignedTaskIds = taskIds.filter((taskId) => {
          return !drivers.some((r) => r.taskIds && r.taskIds.includes(taskId));
        });

        setPendingAssignment({
          taskIds,
          unassignedTaskIds,
          resourceId,
          action: 'assign',
          reassignCount,
        });
        return;
      }

      const taskId = taskIds[0];
      const assignedResource = drivers.find(
        (r) => r.taskIds && r.taskIds.includes(taskId)
      );

      if (assignedResource) {
        if (assignedResource.id === resourceId) {
          return;
        }

        requestReassignment(assignedResource.id, resourceId, taskId);
        return;
      }

      setPendingAssignment({
        taskIds: [taskId],
        unassignedTaskIds: [taskId],
        resourceId,
        action: 'assign',
        reassignCount: 0,
      });
    },
    [driversRef, requestReassignment]
  );

  const requestUnassignment = useCallback(
    (resourceId: number, taskId: number) => {
      setPendingAssignment({
        taskIds: [taskId],
        resourceId,
        action: 'unassign',
      });
    },
    []
  );

  const confirmAssignment = useCallback(async () => {
    if (!pendingAssignment || isLoading) return;

    setIsLoading(true);

    try {
      if (pendingAssignment.action === 'unassign') {
        await unassignTask(
          pendingAssignment.resourceId,
          pendingAssignment.taskIds[0]
        );
      } else if (pendingAssignment.action === 'reassign') {
        const taskIds = pendingAssignment.taskIds;
        if (taskIds.length > 1) {
          await assignTasksBatch(pendingAssignment.resourceId, taskIds);
        } else {
          await reassignTask(
            pendingAssignment.prevResourceId,
            pendingAssignment.resourceId,
            taskIds[0]
          );
        }
      } else {
        const taskIds = pendingAssignment.taskIds;
        if (taskIds.length > 1) {
          await assignTasksBatch(pendingAssignment.resourceId, taskIds);
        } else {
          await assignTask(pendingAssignment.resourceId, taskIds[0]);
        }
      }
    } catch (error) {
      console.error('Failed to complete task assignment action:', error);
    } finally {
      setPendingAssignment(null);
      setIsLoading(false);
    }
  }, [
    pendingAssignment,
    isLoading,
    assignTask,
    assignTasksBatch,
    unassignTask,
    reassignTask,
  ]);

  const cancelAssignment = useCallback(() => {
    setPendingAssignment(null);
  }, []);

  const getRemainingBatteryCount = useCallback(
    (resourceId: number) => {
      const driver = driversRef.current.get(resourceId);
      if (!driver || !driver.vehicleId) {
        return 0;
      }

      const vehicle = vehiclesRef.current.get(driver.vehicleId);
      if (!vehicle) {
        return 0;
      }

      const currentTaskCount = driver.taskIds?.length || 0;
      return Math.max(0, vehicle.batteryCount - currentTaskCount);
    },
    [driversRef, vehiclesRef]
  );

  const getDriverName = useCallback(
    (resourceId: number) => {
      const driver = driversRef.current.get(resourceId);
      return driver?.name || `#${resourceId}`;
    },
    [driversRef]
  );

  const confirmUnassignedOnly = useCallback(async () => {
    if (!pendingAssignment || isLoading) return;
    if (pendingAssignment.action !== 'assign') return;

    const unassignedTaskIds = pendingAssignment.unassignedTaskIds;
    if (unassignedTaskIds.length === 0) {
      setPendingAssignment(null);
      return;
    }

    setIsLoading(true);

    try {
      if (unassignedTaskIds.length > 1) {
        await assignTasksBatch(pendingAssignment.resourceId, unassignedTaskIds);
      } else {
        await assignTask(pendingAssignment.resourceId, unassignedTaskIds[0]);
      }
    } catch (error) {
      console.error('Failed to assign unassigned tasks:', error);
    } finally {
      setPendingAssignment(null);
      setIsLoading(false);
    }
  }, [pendingAssignment, isLoading, assignTask, assignTasksBatch]);

  return (
    <TaskAssignmentContext.Provider
      value={{
        pendingAssignment,
        isLoading,
        requestAssignment,
        requestReassignment,
        requestUnassignment,
        confirmAssignment,
        confirmUnassignedOnly,
        cancelAssignment,
      }}
    >
      {pendingAssignment && (
        <TaskAssignmentBanner
          taskIds={pendingAssignment.taskIds}
          driverName={getDriverName(pendingAssignment.resourceId)}
          prevDriverName={
            pendingAssignment.action === 'reassign' &&
            pendingAssignment.prevResourceId != null
              ? getDriverName(pendingAssignment.prevResourceId)
              : undefined
          }
          remainingBatteryCount={getRemainingBatteryCount(
            pendingAssignment.resourceId
          )}
          action={pendingAssignment.action}
          reassignCount={
            pendingAssignment.action === 'assign'
              ? pendingAssignment.reassignCount
              : 0
          }
          onConfirm={confirmAssignment}
          onConfirmUnassignedOnly={confirmUnassignedOnly}
          onCancel={cancelAssignment}
          isLoading={isLoading}
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
