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
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { Separator } from '~/components/ui/separator';
import { useSimulation } from '~/providers/simulation-provider';
import { type Position, type StationTask } from '~/types';
import { TaskItem } from '../task/task-item';
import { useTaskAssignment } from '~/providers/task-assignment-provider';

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

export interface PopulatedResource {
  id: number;
  position: Position;
  tasks: StationTask[];
  route?: {
    coordinates: Position[];
  };
  inProgressTask: StationTask | null;
}

export type SelectedItemBarElement =
  | { type: SelectedItemType.Station; value: PopulatedStation }
  | { type: SelectedItemType.Driver; value: PopulatedResource };

export default function SelectedItemBar() {
  const { selectedItem, clearSelection } = useSimulation();

  if (!selectedItem) return null;

  const handleClose = () => {
    clearSelection();
  };

  return (
    <div className="absolute top-12 left-4 z-10 w-80">
      <Card className="bg-gray-50">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-lg font-semibold">
            <span className="text-red-500">
              {selectedItem.type === SelectedItemType.Station
                ? 'Station'
                : 'Driver'}
            </span>{' '}
            <span className="text-foreground">#{selectedItem.value.id}</span>
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClose}
            className="h-6 w-6"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <Separator />
        <CardContent>
          {selectedItem.type === SelectedItemType.Station ? (
            <StationInfo station={selectedItem.value} />
          ) : (
            <ResourceInfo resource={selectedItem.value} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StationInfo({ station }: { station: PopulatedStation }) {
  const { driversRef } = useSimulation();
  const { requestUnassignment } = useTaskAssignment();

  return (
    <div className="space-y-2">
      <div>
        <p className="text-sm text-muted-foreground">Name</p>
        <p className="text-sm">{station.name}</p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">Position</p>
        <p className="font-mono text-xs">
          [{station.position[0].toFixed(5)}, {station.position[1].toFixed(5)}]
        </p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">
          Tasks ({station.tasks.length})
        </p>
        {station.tasks.length > 0 ? (
          <div className="space-y-2">
            {station.tasks.map((task) => {
              const assignedResource = Array.from(
                driversRef.current.values()
              ).find((r) => r.taskIds && r.taskIds.includes(task.id));

              return (
                <TaskItem
                  key={task.id}
                  task={task}
                  onUnassign={
                    assignedResource
                      ? () => requestUnassignment(assignedResource.id, task.id)
                      : undefined
                  }
                />
              );
            })}
          </div>
        ) : (
          <p className="text-sm">No tasks</p>
        )}
      </div>
    </div>
  );
}

function ResourceInfo({ resource }: { resource: PopulatedResource }) {
  const { requestUnassignment } = useTaskAssignment();
  const { reorderTasks } = useSimulation();
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  // Track which task is being dragged to distinguish reordering (within same resource)
  // from reassignment (to different resource). Null when dragging from a station.
  const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);

  const handleDragStart = (taskId: number) => setDraggedTaskId(taskId);

  const handleDragEnd = () => {
    setDraggedTaskId(null);
    setDropTargetIndex(null);
  };

  const handleDragOver = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();

    // Only allow reordering if dragging from within this resource's list
    // and not dropping at index 0 (protects in-progress tasks)
    if (draggedTaskId && targetIndex > 0) {
      e.dataTransfer.dropEffect = 'move';
      setDropTargetIndex(targetIndex);
    } else {
      e.dataTransfer.dropEffect = 'none';
    }
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    setDropTargetIndex(null);

    // Prevent reordering if not dragging from this list or dropping at index 0
    if (!draggedTaskId || targetIndex === 0) return;

    const draggedIndex = resource.tasks.findIndex(
      (t) => t.id === draggedTaskId
    );
    // Exit if task not found or dropped at same position
    if (draggedIndex === -1 || draggedIndex === targetIndex) return;

    // Calculate new task order by removing task from old position and inserting at new position
    const taskIds = resource.tasks.map((t) => t.id);
    taskIds.splice(draggedIndex, 1);
    taskIds.splice(targetIndex, 0, draggedTaskId);

    await reorderTasks(resource.id, taskIds, true);
  };

  return (
    <div className="space-y-2">
      <div>
        <p className="text-sm text-muted-foreground">Position</p>
        <p className="font-mono text-xs">
          [{resource.position[0].toFixed(5)}, {resource.position[1].toFixed(5)}]
        </p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">
          Tasks ({resource.tasks.length})
        </p>
        {resource.tasks.length > 0 ? (
          <div className="space-y-2">
            {resource.tasks.map((task, index) => {
              const draggedIndex = draggedTaskId
                ? resource.tasks.findIndex((t) => t.id === draggedTaskId)
                : -1;
              const showDropIndicator = dropTargetIndex === index;
              const isDraggingDown = index > draggedIndex;

              return (
                <div
                  key={task.id}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDrop={(e) => handleDrop(e, index)}
                  onDragStart={() => handleDragStart(task.id)}
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
                    onUnassign={() => requestUnassignment(resource.id, task.id)}
                  />
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm">No tasks assigned</p>
        )}
      </div>
    </div>
  );
}
