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
import { X } from 'lucide-react';
import { useSimulation } from '~/providers/simulation-provider';
import { DriverState, type Position, type StationTask } from '~/types';
import { TaskItem } from '../task/task-item';
import { useTaskAssignment } from '~/providers/task-assignment-provider';
import { ScrollArea } from '~/components/ui/scroll-area';
import { Button } from '../ui/button';
import DriverStateBadge from './driver-state-badge';
import { useTaskMassSelect } from '~/hooks/use-task-mass-select';

export enum SelectedItemType {
  Station = 'station',
  Driver = 'driver',
}

export interface PopulatedStation {
  id: number;
  name: string;
  position: Position;
  tasks: StationTask[];
}

export interface PopulatedDriver {
  id: number;
  name: string;
  position: Position;
  tasks: StationTask[];
  route?: {
    coordinates: Position[];
  };
  state: DriverState;
  inProgressTask: StationTask | null;
}

export type SelectedItemBarElement =
  | { type: SelectedItemType.Station; value: PopulatedStation }
  | { type: SelectedItemType.Driver; value: PopulatedDriver };

export default function SelectedItemBar() {
  const { selectedItem, clearSelection } = useSimulation();

  if (!selectedItem) return null;

  const handleClose = () => {
    clearSelection();
  };

  return (
    <div className="bg-gray-50 flex flex-col gap-2 rounded-lg border py-4 shadow-sm">
      <div className="px-5 flex flex-row justify-between items-start gap-1">
        <div className="flex flex-col">
          <span className="text-xl font-bold">{selectedItem.value.name}</span>
          {selectedItem.type === SelectedItemType.Driver && (
            <div className="flex flex row gap-2">
              <span className="text-muted-foreground text-sm font-normal">
                Driver #{selectedItem.value.id}
              </span>
              <DriverStateBadge state={selectedItem.value.state} />
            </div>
          )}
          {selectedItem.type === SelectedItemType.Station && (
            <span className="text-muted-foreground text-sm font-normal">
              Station #{selectedItem.value.id}
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClose}
          className="h-7 w-7"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      <p className="text-sm text-muted-foreground px-5">
        {selectedItem.value.tasks.length === 0
          ? 'No tasks'
          : `Tasks (${selectedItem.value.tasks.length})`}
      </p>
      {selectedItem.value.tasks.length > 0 && (
        <ScrollArea className="mx-2">
          <div className="max-h-50 px-3 space-y-1">
            {selectedItem.type === SelectedItemType.Station ? (
              <StationTasks station={selectedItem.value} />
            ) : (
              <DriverTasks driver={selectedItem.value} />
            )}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}

function StationTasks({ station }: { station: PopulatedStation }) {
  const { driversRef } = useSimulation();
  const { requestUnassignment } = useTaskAssignment();
  const taskIds = station.tasks.map((task) => task.id);
  const { selectedTaskIds, handleTaskSelect, selectForDrag } =
    useTaskMassSelect(taskIds, station.id);

  return (
    <>
      {station.tasks.map((task, index) => {
        const assignedResource = Array.from(driversRef.current.values()).find(
          (r) => r.taskIds.includes(task.id)
        );

        return (
          <TaskItem
            key={task.id}
            task={task}
            isSelected={selectedTaskIds.includes(task.id)}
            onSelect={(event) => handleTaskSelect(task.id, index, event)}
            onDragStart={() => selectForDrag(task.id, index)}
            getDragTaskIds={() =>
              selectedTaskIds.includes(task.id) ? selectedTaskIds : [task.id]
            }
            onUnassign={
              assignedResource
                ? () => requestUnassignment(assignedResource.id, task.id)
                : undefined
            }
          />
        );
      })}
    </>
  );
}

function DriverTasks({ driver }: { driver: PopulatedDriver }) {
  const { requestUnassignment } = useTaskAssignment();
  const { reorderTasks } = useSimulation();
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  // Track which task is being dragged to distinguish reordering (within same driver)
  // from reassignment (to different driver). Null when dragging from a station.
  const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);
  const taskIds = driver.tasks.map((task) => task.id);
  const { selectedTaskIds, handleTaskSelect, selectForDrag } =
    useTaskMassSelect(taskIds, driver.id);

  const handleDragStart = (taskId: number, taskIndex: number) => {
    selectForDrag(taskId, taskIndex);
    setDraggedTaskId(taskId);
  };

  const handleDragEnd = () => {
    setDraggedTaskId(null);
    setDropTargetIndex(null);
  };

  const handleDragOver = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();

    // Only allow reordering if dragging from within this driver's list
    if (draggedTaskId) {
      e.dataTransfer.dropEffect = 'move';
      setDropTargetIndex(targetIndex);
    } else {
      e.dataTransfer.dropEffect = 'none';
    }
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    setDropTargetIndex(null);

    // Prevent reordering if not dragging from this list
    if (!draggedTaskId) return;

    const draggedIndex = driver.tasks.findIndex((t) => t.id === draggedTaskId);
    // Exit if task not found or dropped at same position
    if (draggedIndex === -1 || draggedIndex === targetIndex) return;

    // Calculate new task order by removing task from old position and inserting at new position
    const taskIds = driver.tasks.map((t) => t.id);
    taskIds.splice(draggedIndex, 1);
    taskIds.splice(targetIndex, 0, draggedTaskId);

    await reorderTasks(driver.id, taskIds, true);
  };

  return (
    <>
      {driver.tasks.map((task, index) => {
        const draggedIndex = draggedTaskId
          ? driver.tasks.findIndex((t) => t.id === draggedTaskId)
          : -1;
        const showDropIndicator = dropTargetIndex === index;
        const isDraggingDown = index > draggedIndex;

        return (
          <div
            key={task.id}
            onDragOver={(e) => handleDragOver(e, index)}
            onDrop={(e) => handleDrop(e, index)}
            onDragEnd={handleDragEnd}
            className={
              showDropIndicator
                ? isDraggingDown
                  ? 'border-b-2 border-blue-500 pb-1'
                  : 'border-t-2 border-blue-500 pt-1'
                : ''
            }
          >
            <TaskItem
              task={task}
              isSelected={selectedTaskIds.includes(task.id)}
              onSelect={(event) => handleTaskSelect(task.id, index, event)}
              onDragStart={() => handleDragStart(task.id, index)}
              getDragTaskIds={() =>
                selectedTaskIds.includes(task.id) ? selectedTaskIds : [task.id]
              }
              onUnassign={() => requestUnassignment(driver.id, task.id)}
            />
          </div>
        );
      })}
    </>
  );
}
