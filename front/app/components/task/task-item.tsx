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

export function TaskItem({
  taskId,
  onUnassign,
}: {
  taskId: number;
  onUnassign?: () => void;
}) {
  const dragEnabled = useFeature('taskDragAndDrop');

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('taskId', taskId.toString());
  };

  return (
    <Item
      draggable={dragEnabled}
      onDragStart={handleDragStart}
      className={`rounded-lg px-3 py-2 bg-white border border-gray-200
        hover:border-gray-300 transition-all duration-200 ${
          dragEnabled
            ? 'cursor-grab hover:shadow-sm active:cursor-grabbing active:opacity-50'
            : 'cursor-default'
        }`}
    >
      <ItemContent>
        <ItemTitle>Task #{taskId}</ItemTitle>
      </ItemContent>
      {onUnassign ? (
        <Button
          variant="ghost"
          size="icon"
          onClick={onUnassign}
          className="h-6 w-6"
        >
          <X className="h-4 w-4" />
        </Button>
      ) : null}
    </Item>
  );
}
