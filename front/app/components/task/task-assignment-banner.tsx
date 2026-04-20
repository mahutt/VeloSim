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
import usePreferences from '~/hooks/use-preferences';
import { formatTranslation } from '~/lib/i18n';

export function TaskAssignmentBanner() {
  const { state, engine } = useSimulation();
  const { t } = usePreferences();
  const {
    blockAssignments,
    pendingAssignment,
    pendingAssignmentLoading: isLoading,
  } = state;

  const [loadingAction, setLoadingAction] = useState<
    'all' | 'remaining' | null
  >(null);
  if (blockAssignments || !pendingAssignment) return null;

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
    isAllReassign || action === TaskAction.Reassign
      ? t.map.assignment.reassign
      : t.map.assignment.assign;

  const exceedsBattery =
    count > pendingAssignment.driverBatteryCount &&
    (action === TaskAction.Assign || action === TaskAction.Reassign);

  const driverName = pendingAssignment.driverName;
  const remainingBatteryCount = pendingAssignment.driverBatteryCount;
  const prevDriverName =
    (pendingAssignment as ReassignTaskAction).prevDriverName ?? undefined;
  const unassignStationName =
    pendingAssignment.action === TaskAction.Unassign
      ? pendingAssignment.stationName
      : undefined;

  const renderMessage = () => {
    if (!count) return null;
    const taskWord =
      count === 1 ? t.map.labels.taskSingular : t.map.labels.taskPlural;
    const reassignTaskWord =
      reassignCount === 1 ? t.map.labels.taskSingular : t.map.labels.taskPlural;

    // Battery warning (assign / reassign only)
    if (exceedsBattery) {
      const batteryWord =
        remainingBatteryCount === 1
          ? t.map.assignment.batterySingular
          : t.map.assignment.batteryPlural;
      return (
        <>
          <span className="block">
            {formatTranslation(t.map.assignment.driverHasBatteries, {
              driver: driverName,
              count: remainingBatteryCount,
              batteryWord,
            })}
          </span>
          <span className="block">
            {formatTranslation(t.map.assignment.assignTasksAnyway, {
              action: actionLabel,
              count,
              taskWord,
            })}
          </span>
          {hasMixedTasks && (
            <span className="block text-muted-foreground">
              {formatTranslation(t.map.assignment.alreadyAssigned, {
                count: reassignCount,
                taskWord: reassignTaskWord,
              })}
            </span>
          )}
        </>
      );
    }

    // Unassign
    if (action === TaskAction.Unassign) {
      if (isMulti) {
        return unassignStationName
          ? formatTranslation(
              t.taskAssignmentBanner.unassign.multi.withStation,
              {
                count,
                stationName: unassignStationName,
                driverName,
              }
            )
          : formatTranslation(
              t.taskAssignmentBanner.unassign.multi.withoutStation,
              {
                count,
                driverName,
              }
            );
      }

      return unassignStationName
        ? formatTranslation(
            t.taskAssignmentBanner.unassign.single.withStation,
            {
              taskId: firstTaskId,
              stationName: unassignStationName,
              driverName,
            }
          )
        : formatTranslation(
            t.taskAssignmentBanner.unassign.single.withoutStation,
            {
              taskId: firstTaskId,
              driverName,
            }
          );
    }

    // Reassign from a single known driver
    if (action === TaskAction.Reassign && prevDriverName !== undefined) {
      return isMulti
        ? formatTranslation(t.map.assignment.reassignMultiFromTo, {
            count,
            from: prevDriverName,
            to: driverName,
          })
        : formatTranslation(t.map.assignment.reassignSingleFromTo, {
            taskId: firstTaskId,
            from: prevDriverName,
            to: driverName,
          });
    }

    // All tasks already assigned (multiple source drivers)
    if (isAllReassign) {
      return formatTranslation(t.map.assignment.reassignMultiTo, {
        count,
        to: driverName,
      });
    }

    // Mixed batch (some assigned, some not)
    if (hasMixedTasks) {
      return (
        <>
          <span className="block">
            {formatTranslation(t.map.assignment.assignMultiTo, {
              count,
              to: driverName,
            })}
          </span>
          <span className="block text-muted-foreground">
            {formatTranslation(t.map.assignment.alreadyAssigned, {
              count: reassignCount,
              taskWord: reassignTaskWord,
            })}
          </span>
        </>
      );
    }

    // Pure assign
    return isMulti
      ? formatTranslation(t.map.assignment.assignMultiTo, {
          count,
          to: driverName,
        })
      : formatTranslation(t.map.assignment.assignSingleTo, {
          taskId: firstTaskId,
          to: driverName,
        });
  };

  return (
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
          {t.common.cancel}
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
                ? t.map.assignment.assigning
                : formatTranslation(t.map.assignment.remaining, {
                    count: unassignedCount,
                  })}
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
                ? t.map.assignment.assigning
                : formatTranslation(t.map.assignment.all, {
                    count: taskIds.length,
                  })}
            </Button>
          </>
        ) : (
          <Button
            onClick={() => engine.confirmAssignment()}
            size="sm"
            disabled={isLoading}
            aria-busy={isLoading}
          >
            {isLoading ? t.map.assignment.confirming : t.map.assignment.confirm}
          </Button>
        )}
      </div>
    </div>
  );
}
