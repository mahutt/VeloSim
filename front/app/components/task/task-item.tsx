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

import { Item, ItemContent, ItemTitle } from '~/components/ui/item';
import { useFeature } from '~/hooks/use-feature';
import { Button } from '~/components/ui/button';
import { X } from 'lucide-react';
import type { StationTask } from '~/types';

export function TaskItem({
  task,
  onUnassign,
  onSelect,
  isSelected = false,
  onDragStart,
  getDragTaskIds,
}: {
  task: StationTask;
  onUnassign?: () => void;
  onSelect?: (event: React.MouseEvent<HTMLDivElement>) => void;
  isSelected?: boolean;
  onDragStart?: (event: React.DragEvent<HTMLDivElement>) => void;
  getDragTaskIds?: () => number[];
}) {
  const taskIsInProgress = task.state === 'inprogress';
  const taskIsInService = task.state === 'inservice';

  const dragEnabled = useFeature('taskDragAndDrop') && !taskIsInService;

  const handleSelect = (event: React.MouseEvent<HTMLDivElement>) => {
    if (taskIsInService) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    onSelect?.(event);
  };

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    onDragStart?.(e);
    e.dataTransfer.effectAllowed = 'move';
    const draggedTaskIds = getDragTaskIds?.() ?? [task.id];

    e.dataTransfer.setData('taskIds', JSON.stringify(draggedTaskIds));

    // custom preview for multiple tasks dragging
    if (draggedTaskIds.length > 1) {
      const dragPreview = document.createElement('div');
      dragPreview.className = 'px-2 bg-blue-500 text-white rounded-lg';
      dragPreview.innerHTML = `<span>${draggedTaskIds.length} tasks</span>`;
      dragPreview.style.position = 'absolute';
      document.body.appendChild(dragPreview);
      e.dataTransfer.setDragImage(dragPreview, 0, 0);

      requestAnimationFrame(() => {
        if (document.body.contains(dragPreview)) {
          document.body.removeChild(dragPreview);
        }
      });
    }
  };

  return (
    <Item
      draggable={dragEnabled}
      onDragStart={handleDragStart}
      onClick={handleSelect}
      className={`rounded-lg px-3 py-2 bg-white border border-gray-200 h-10
        ${
          dragEnabled
            ? 'cursor-grab hover:shadow-sm active:cursor-grabbing active:opacity-50'
            : 'cursor-default'
        } ${isSelected ? 'border-blue-500 bg-blue-50' : ''}`}
    >
      <ItemContent>
        <ItemTitle>Task #{task.id}</ItemTitle>
      </ItemContent>
      {taskIsInService ? (
        <span className="text-sm text-gray-500 italic">In Service</span>
      ) : onUnassign ? (
        <>
          {taskIsInProgress && (
            <span className="text-sm text-gray-500 italic">In Progress</span>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={(event) => {
              event.stopPropagation();
              onUnassign?.();
            }}
            className="h-6 w-6"
          >
            <X className="h-4 w-4" />
          </Button>
        </>
      ) : null}
    </Item>
  );
}
