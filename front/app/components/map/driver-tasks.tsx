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
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useSimulation } from '~/providers/simulation-provider';
import { type StationTask } from '~/types';
import { TaskItem } from '../task/task-item';
import { Button } from '~/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '~/components/ui/tooltip';
import { useTaskMassSelect } from '~/hooks/use-task-mass-select';
import type { PopulatedDriver } from './selected-item-bar';
import { ScrollArea } from '~/components/ui/scroll-area';

interface DriverTaskStationGroup {
  stationId: number;
  stationName: string;
  tasks: StationTask[];
}

function groupDriverTasksByStation(
  tasks: StationTask[],
  resolveStationName: (stationId: number) => string
): DriverTaskStationGroup[] {
  const groups: DriverTaskStationGroup[] = [];

  for (const task of tasks) {
    const lastGroup = groups[groups.length - 1];
    if (lastGroup && lastGroup.stationId === task.stationId) {
      lastGroup.tasks.push(task);
      continue;
    }

    groups.push({
      stationId: task.stationId,
      stationName: resolveStationName(task.stationId),
      tasks: [task],
    });
  }

  return groups;
}

function CollapseToggle({
  isCollapsed,
  onToggle,
}: {
  isCollapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      onClick={onToggle}
      className="h-6 w-6 shrink-0"
      aria-label={isCollapsed ? 'Expand task list' : 'Collapse task list'}
    >
      <span className="flex flex-col items-center leading-none">
        {isCollapsed ? (
          <>
            <ChevronDown className="h-3 w-3 -mb-0.5" />
            <ChevronUp className="h-3 w-3 -mt-0.5" />
          </>
        ) : (
          <>
            <ChevronUp className="h-3 w-3 -mb-0.5" />
            <ChevronDown className="h-3 w-3 -mt-0.5" />
          </>
        )}
      </span>
    </Button>
  );
}

function DriverTaskGroupItem({
  group,
  index,
  showDropIndicator,
  isDraggingDown,
  isDraggedGroup,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  group: DriverTaskStationGroup;
  index: number;
  showDropIndicator: boolean;
  isDraggingDown: boolean;
  isDraggedGroup: boolean;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, index: number) => void;
  onDragOver: (e: React.DragEvent<HTMLDivElement>, index: number) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>, index: number) => void;
  onDragEnd: () => void;
}) {
  return (
    <div
      onDragOver={(e) => onDragOver(e, index)}
      onDrop={(e) => onDrop(e, index)}
      onDragEnd={onDragEnd}
      className={
        showDropIndicator
          ? isDraggingDown
            ? 'border-b-2 border-blue-500 pb-1'
            : 'border-t-2 border-blue-500 pt-1'
          : ''
      }
    >
      <div
        draggable
        onDragStart={(e) => onDragStart(e, index)}
        className={`rounded-lg px-3 py-2 border h-10 text-sm flex items-center gap-2 w-full min-w-0 overflow-hidden cursor-grab active:cursor-grabbing active:opacity-50 ${
          isDraggedGroup
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-200 bg-white'
        }`}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="block text-sm font-medium text-foreground min-w-0 max-w-40 truncate">
              {group.stationName}
            </span>
          </TooltipTrigger>
          <TooltipContent side="top" sideOffset={6}>
            {group.stationName}
          </TooltipContent>
        </Tooltip>
        <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0 ml-auto">
          {group.tasks.length} {group.tasks.length === 1 ? 'task' : 'tasks'}
        </span>
      </div>
    </div>
  );
}

function DriverTasksCollapsed({
  groupedTasks,
  onReorder,
}: {
  groupedTasks: DriverTaskStationGroup[];
  onReorder: (taskIds: number[]) => Promise<void>;
}) {
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const [draggedGroupIndex, setDraggedGroupIndex] = useState<number | null>(
    null
  );

  const handleDragStart = (
    e: React.DragEvent<HTMLDivElement>,
    groupIndex: number
  ) => {
    e.dataTransfer.effectAllowed = 'move';
    setDraggedGroupIndex(groupIndex);
  };

  const handleDragOver = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedGroupIndex === null) {
      e.dataTransfer.dropEffect = 'none';
      return;
    }
    e.dataTransfer.dropEffect = 'move';
    if (dropTargetIndex !== targetIndex) setDropTargetIndex(targetIndex);
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    setDropTargetIndex(null);

    const sourceIndex = draggedGroupIndex;
    if (sourceIndex === null || sourceIndex === targetIndex) return;

    const groupTaskIds = groupedTasks.map((g) => g.tasks.map((t) => t.id));
    const [movedGroup] = groupTaskIds.splice(sourceIndex, 1);
    if (!movedGroup) return;
    groupTaskIds.splice(targetIndex, 0, movedGroup);

    await onReorder(groupTaskIds.flat());
  };

  const handleDragEnd = () => {
    setDraggedGroupIndex(null);
    setDropTargetIndex(null);
  };

  return (
    <>
      {groupedTasks.map((group, index) => (
        <DriverTaskGroupItem
          key={`${group.stationId}-${index}`}
          group={group}
          index={index}
          showDropIndicator={
            dropTargetIndex === index && draggedGroupIndex !== index
          }
          isDraggingDown={
            draggedGroupIndex !== null && index > draggedGroupIndex
          }
          isDraggedGroup={draggedGroupIndex === index}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragEnd={handleDragEnd}
        />
      ))}
    </>
  );
}

function DriverTasksExpanded({
  driver,
  resolveStationName,
  selectedTaskIds,
  handleTaskSelect,
  selectForDrag,
  onReorder,
  onUnassign,
}: {
  driver: PopulatedDriver;
  resolveStationName: (stationId: number) => string;
  selectedTaskIds: number[];
  handleTaskSelect: (
    taskId: number,
    index: number,
    event: React.MouseEvent<HTMLDivElement>
  ) => void;
  selectForDrag: (taskId: number, index: number) => void;
  onReorder: (taskIds: number[]) => Promise<void>;
  onUnassign: (taskId: number) => void;
}) {
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);

  const draggedIndex = draggedTaskId
    ? driver.tasks.findIndex((t) => t.id === draggedTaskId)
    : -1;

  const handleDragStart = (taskId: number, taskIndex: number) => {
    selectForDrag(taskId, taskIndex);
    setDraggedTaskId(taskId);
  };

  const handleDragOver = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (!draggedTaskId) {
      e.dataTransfer.dropEffect = 'none';
      return;
    }
    e.dataTransfer.dropEffect = 'move';
    if (dropTargetIndex !== targetIndex) setDropTargetIndex(targetIndex);
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    setDropTargetIndex(null);
    if (!draggedTaskId) return;

    if (draggedIndex === -1 || draggedIndex === targetIndex) return;

    const taskIds = driver.tasks.map((t) => t.id);
    taskIds.splice(draggedIndex, 1);
    taskIds.splice(targetIndex, 0, draggedTaskId);

    await onReorder(taskIds);
  };

  const handleDragEnd = () => {
    setDraggedTaskId(null);
    setDropTargetIndex(null);
  };

  return (
    <>
      {driver.tasks.map((task, index) => (
        <div
          key={task.id}
          onDragOver={(e) => handleDragOver(e, index)}
          onDrop={(e) => handleDrop(e, index)}
          onDragEnd={handleDragEnd}
          className={
            dropTargetIndex === index && index !== draggedIndex
              ? index > draggedIndex
                ? 'border-b-2 border-blue-500 pb-1'
                : 'border-t-2 border-blue-500 pt-1'
              : ''
          }
        >
          <TaskItem
            task={task}
            stationName={resolveStationName(task.stationId)}
            isSelected={selectedTaskIds.includes(task.id)}
            onSelect={(event) => handleTaskSelect(task.id, index, event)}
            onDragStart={() => handleDragStart(task.id, index)}
            getDragTaskIds={() =>
              selectedTaskIds.includes(task.id) ? selectedTaskIds : [task.id]
            }
            onUnassign={() => onUnassign(task.id)}
          />
        </div>
      ))}
    </>
  );
}

export function DriverTasks({ driver }: { driver: PopulatedDriver }) {
  const { engine } = useSimulation();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const taskIds = driver.tasks.map((t) => t.id);
  const { selectedTaskIds, handleTaskSelect, selectForDrag } =
    useTaskMassSelect(taskIds, driver.id);

  const resolveStationName = (stationId: number) =>
    engine.state?.getStation(stationId)?.name ?? `Station #${stationId}`;

  const groupedTasks = groupDriverTasksByStation(
    driver.tasks,
    resolveStationName
  );

  return (
    <>
      <div className="px-5 flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {selectedTaskIds.length > 0
            ? `Tasks (${selectedTaskIds.length}/${driver.tasks.length} selected)`
            : `Tasks (${driver.tasks.length})`}
        </p>
        <CollapseToggle
          isCollapsed={isCollapsed}
          onToggle={() => setIsCollapsed((prev) => !prev)}
        />
      </div>
      <ScrollArea className="mx-2">
        <div className="max-h-50 px-3 space-y-1">
          {isCollapsed ? (
            <DriverTasksCollapsed
              groupedTasks={groupedTasks}
              onReorder={(ids) => engine.reorderTasks(driver.id, ids, true)}
            />
          ) : (
            <DriverTasksExpanded
              driver={driver}
              resolveStationName={resolveStationName}
              selectedTaskIds={selectedTaskIds}
              handleTaskSelect={handleTaskSelect}
              selectForDrag={selectForDrag}
              onReorder={(ids) => engine.reorderTasks(driver.id, ids, true)}
              onUnassign={(taskId) =>
                engine.requestUnassignment(driver.id, taskId)
              }
            />
          )}
        </div>
      </ScrollArea>
    </>
  );
}
