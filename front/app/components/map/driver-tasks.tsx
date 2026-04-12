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
import { X } from 'lucide-react';
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
import { useAutoScroll } from '~/hooks/use-auto-scroll';
import type { PopulatedDriver } from './selected-item-bar';
import { ScrollArea } from '~/components/ui/scroll-area';
import usePreferences from '~/hooks/use-preferences';
import { formatTranslation, type TranslationSchema } from '~/lib/i18n';
import { setTaskDragDataAndPreview } from '~/lib/task-drag';

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
  isSelected,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  onClick,
  onContextMenu,
  onMouseDown,
  onMouseEnter,
  onUnassign,
}: {
  group: DriverTaskStationGroup;
  index: number;
  showDropIndicator: boolean;
  isDraggingDown: boolean;
  isDraggedGroup: boolean;
  isSelected: boolean;
  onDragStart: (e: React.DragEvent<HTMLDivElement>, index: number) => void;
  onDragOver: (e: React.DragEvent<HTMLDivElement>, index: number) => void;
  onDrop: (e: React.DragEvent<HTMLDivElement>, index: number) => void;
  onDragEnd: () => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
  onContextMenu: (e: React.MouseEvent) => void;
  onMouseDown: (e: React.MouseEvent) => void;
  onMouseEnter: () => void;
  onUnassign: () => void;
}) {
  const { t } = usePreferences();
  const { engine } = useSimulation();

  return (
    <div
      onDragOver={(e) => onDragOver(e, index)}
      onDrop={(e) => onDrop(e, index)}
      onDragEnd={onDragEnd}
      onClick={onClick}
      onContextMenu={onContextMenu}
      onMouseDown={onMouseDown}
      onMouseEnter={() => {
        onMouseEnter();
        engine.setTaskHoveredStationId(group.stationId);
      }}
      onMouseLeave={() => {
        engine.setTaskHoveredStationId(null);
      }}
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
          isDraggedGroup || isSelected
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-200 bg-white'
        }`}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="block text-sm font-medium text-foreground min-w-0 max-w-32 truncate">
              {group.stationName}
            </span>
          </TooltipTrigger>
          <TooltipContent side="top" sideOffset={6}>
            {group.stationName}
          </TooltipContent>
        </Tooltip>
        <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0 ml-auto">
          {group.tasks.length}{' '}
          {group.tasks.length === 1
            ? t.map.labels.taskSingular
            : t.map.labels.taskPlural}
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={(event) => {
            event.stopPropagation();
            onUnassign();
          }}
          className="h-6 w-6"
          aria-label={`Unassign ${group.tasks.length} ${group.tasks.length === 1 ? 'task' : 'tasks'} at ${group.stationName}`}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function DriverTasksCollapsed({
  groupedTasks,
  selectedTaskIds,
  handleTaskSelect,
  startDragSelect,
  dragSelectEnter,
  onReorder,
  onUnassign,
}: {
  groupedTasks: DriverTaskStationGroup[];
  selectedTaskIds: number[];
  handleTaskSelect: (
    taskId: number,
    index: number,
    event: React.MouseEvent<HTMLDivElement>
  ) => void;
  startDragSelect: (taskId: number, ctrlKey: boolean) => void;
  dragSelectEnter: (taskId: number) => void;
  onReorder: (taskIds: number[]) => Promise<void>;
  onUnassign: (taskIds: number[], stationName: string) => void;
}) {
  const { t } = usePreferences();
  const selectedGroupIndices = new Set(
    groupedTasks
      .map((g, i) =>
        g.tasks.some((t) => selectedTaskIds.includes(t.id)) ? i : -1
      )
      .filter((i) => i !== -1)
  );
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const [draggedGroupIndex, setDraggedGroupIndex] = useState<number | null>(
    null
  );

  const handleDragStart = (
    e: React.DragEvent<HTMLDivElement>,
    groupIndex: number
  ) => {
    const draggedGroup = groupedTasks[groupIndex];
    if (!draggedGroup) return;

    const groupsToMove = selectedGroupIndices.has(groupIndex)
      ? groupedTasks.filter((_, i) => selectedGroupIndices.has(i))
      : [draggedGroup];

    const dragTaskIds = groupsToMove.flatMap((g) => g.tasks.map((t) => t.id));
    setTaskDragDataAndPreview(e, dragTaskIds, t.map.labels.taskPlural);

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

    // Multi-group reorder: if the dragged group is selected, move all selected groups
    const movingIndices = selectedGroupIndices.has(sourceIndex)
      ? [...selectedGroupIndices].sort((a, b) => a - b)
      : [sourceIndex];

    if (movingIndices.some((i) => i === targetIndex)) return;

    const movingSet = new Set(movingIndices);
    const movedGroups = movingIndices.map((i) => {
      const group = groupTaskIds[i];
      if (!group) throw new Error(`Invalid group index ${i}`);
      return group;
    });
    const remaining = groupTaskIds.filter((_, i) => !movingSet.has(i));

    // Calculate where to insert in the remaining array
    // targetIndex in the original array maps to a position in `remaining`
    const adjustedTarget =
      targetIndex - movingIndices.filter((mi) => mi < targetIndex).length;
    const insertAt =
      sourceIndex < targetIndex ? adjustedTarget + 1 : adjustedTarget;

    remaining.splice(insertAt, 0, ...movedGroups);

    await onReorder(remaining.flat());
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
          isSelected={selectedGroupIndices.has(index)}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragEnd={handleDragEnd}
          onClick={(e) => {
            const firstTaskId = group.tasks[0].id;
            const flatIndex = groupedTasks
              .slice(0, index)
              .reduce((sum, g) => sum + g.tasks.length, 0);
            handleTaskSelect(firstTaskId, flatIndex, e);
          }}
          onContextMenu={(e) => e.preventDefault()}
          onMouseDown={(e) => {
            if (e.button === 2) {
              e.preventDefault();
              startDragSelect(group.tasks[0].id, e.ctrlKey || e.metaKey);
            }
          }}
          onMouseEnter={() =>
            dragSelectEnter(group.tasks[group.tasks.length - 1].id)
          }
          onUnassign={() =>
            onUnassign(
              group.tasks.map((task) => task.id),
              group.stationName
            )
          }
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
  startDragSelect,
  dragSelectEnter,
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
  selectForDrag: (taskId: number) => void;
  startDragSelect: (taskId: number, ctrlKey: boolean) => void;
  dragSelectEnter: (taskId: number) => void;
  onReorder: (taskIds: number[]) => Promise<void>;
  onUnassign: (taskId: number) => void;
}) {
  const { engine } = useSimulation();
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null);
  const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);

  const draggedIndex = draggedTaskId
    ? driver.tasks.findIndex((t) => t.id === draggedTaskId)
    : -1;

  const handleDragStart = (taskId: number) => {
    selectForDrag(taskId);
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
    const draggingSet = new Set(
      selectedTaskIds.includes(draggedTaskId)
        ? selectedTaskIds
        : [draggedTaskId]
    );

    // Exit if the drop target is one of the tasks being moved
    if (draggingSet.has(driver.tasks[targetIndex]?.id)) return;

    const remaining = taskIds.filter((id) => !draggingSet.has(id));
    const movedIds = taskIds.filter((id) => draggingSet.has(id));

    // Calculate insert position in the remaining array
    const adjustedTarget =
      targetIndex -
      taskIds.slice(0, targetIndex).filter((id) => draggingSet.has(id)).length;
    const insertAt =
      draggedIndex < targetIndex ? adjustedTarget + 1 : adjustedTarget;

    remaining.splice(insertAt, 0, ...movedIds);

    await onReorder(remaining);
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
          onContextMenu={(e) => e.preventDefault()}
          onMouseDown={(e) => {
            if (e.button === 2) {
              e.preventDefault();
              startDragSelect(task.id, e.ctrlKey || e.metaKey);
            }
          }}
          onMouseEnter={() => {
            dragSelectEnter(task.id);
            engine.setTaskHoveredStationId(task.stationId);
          }}
          onMouseLeave={() => engine.setTaskHoveredStationId(null)}
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
            onDragStart={() => handleDragStart(task.id)}
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
  const { t } = usePreferences();
  const [isCollapsed, setIsCollapsed] = useState(true);

  const taskIds = driver.tasks.map((t) => t.id);
  const {
    selectedTaskIds,
    isDragSelecting,
    handleTaskSelect,
    selectForDrag,
    startDragSelect,
    dragSelectEnter,
    clearSelection,
  } = useTaskMassSelect(taskIds, driver.id);
  const { containerRef, handleMouseMove } = useAutoScroll(isDragSelecting);

  const resolveStationName = (stationId: number) =>
    engine.state?.getStation(stationId)?.name ??
    formatTranslation(t.map.labels.stationFallback, {
      id: stationId,
    });

  const groupedTasks = groupDriverTasksByStation(
    driver.tasks,
    resolveStationName
  );

  return (
    <>
      <div className="px-5 flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {GenerateTaskListLabel(
            isCollapsed,
            selectedTaskIds.length,
            driver.tasks.length,
            t
          )}
        </p>
        <CollapseToggle
          isCollapsed={isCollapsed}
          onToggle={() => {
            clearSelection();
            setIsCollapsed((prev) => !prev);
          }}
        />
      </div>
      <ScrollArea className="mx-2">
        <div
          ref={containerRef}
          onMouseMove={handleMouseMove}
          className="max-h-50 px-3 space-y-1"
          onMouseLeave={() => engine.setTaskHoveredStationId(null)}
        >
          {isCollapsed ? (
            <DriverTasksCollapsed
              groupedTasks={groupedTasks}
              selectedTaskIds={selectedTaskIds}
              handleTaskSelect={handleTaskSelect}
              startDragSelect={startDragSelect}
              dragSelectEnter={dragSelectEnter}
              onReorder={(ids) => engine.reorderTasks(driver.id, ids, true)}
              onUnassign={(taskIds, stationName) =>
                engine.requestUnassignment(driver.id, taskIds, stationName)
              }
            />
          ) : (
            <DriverTasksExpanded
              driver={driver}
              resolveStationName={resolveStationName}
              selectedTaskIds={selectedTaskIds}
              handleTaskSelect={handleTaskSelect}
              selectForDrag={selectForDrag}
              startDragSelect={startDragSelect}
              dragSelectEnter={dragSelectEnter}
              onReorder={(ids) => engine.reorderTasks(driver.id, ids, true)}
              onUnassign={(taskId) =>
                engine.requestUnassignment(driver.id, [taskId])
              }
            />
          )}
        </div>
      </ScrollArea>
    </>
  );
}

export function GenerateTaskListLabel(
  collapsed: boolean,
  selectedCount: number,
  totalCount: number,
  t: TranslationSchema
) {
  if (!collapsed) {
    return selectedCount > 0
      ? formatTranslation(t.map.labels.tasksSelectedCount, {
          selected: selectedCount,
          total: totalCount,
        })
      : formatTranslation(t.map.labels.tasksCount, {
          count: totalCount,
        });
  }

  // Assume collapsed state
  const singular = totalCount === 1;
  if (selectedCount === 0) {
    return `${t.map.labels.itinerary} (${totalCount} ${singular ? t.map.labels.taskSingular : t.map.labels.taskPlural})`;
  }

  // Assume collapsed state with selection
  return `${t.map.labels.itinerary} (${selectedCount}/${totalCount} ${t.map.labels.taskPlural})`;
}
