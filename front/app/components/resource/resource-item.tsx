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
import { Item, ItemContent, ItemTitle } from '~/components/ui/item';
import { useTaskAssignment } from '~/providers/task-assignment-provider';
import { Battery, BatteryLow, BatteryMedium, BatteryFull } from 'lucide-react';

function getBatteryIconAndColor(
  batteryCount: number,
  batteryCapacity: number
): {
  Icon:
    | typeof Battery
    | typeof BatteryLow
    | typeof BatteryMedium
    | typeof BatteryFull;
  color: string;
} {
  const percentage = (batteryCount / batteryCapacity) * 100;

  if (percentage === 0) {
    return {
      Icon: Battery,
      color: 'text-red-500',
    };
  }

  if (percentage <= 40) {
    return {
      Icon: BatteryLow,
      color: 'text-orange-500',
    };
  }

  if (percentage <= 75) {
    return {
      Icon: BatteryMedium,
      color: 'text-yellow-500',
    };
  }

  return {
    Icon: BatteryFull,
    color: 'text-green-500',
  };
}

// Restricted Resource type for ResourceItem component
export interface ResourceItemElement {
  id: number;
  name: string;
  taskCount: number;
  batteryCount: number;
  batteryCapacity: number;
}

export function ResourceItem({
  resource,
  onSelect,
  isSelected = false,
}: {
  resource: ResourceItemElement;
  onSelect: () => void;
  isSelected?: boolean;
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const { requestAssignment } = useTaskAssignment();

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDropOnResource = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const taskIdsPayload = e.dataTransfer.getData('taskIds');
    if (taskIdsPayload) {
      try {
        const taskIds = JSON.parse(taskIdsPayload || '[]');
        if (taskIds.length === 0) return;

        requestAssignment(resource.id, taskIds);
      } catch {
        return;
      }
    }
  };

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    const target = e.relatedTarget as Node | null;
    if (target && e.currentTarget.contains(target)) {
      return;
    }
    setIsDragOver(false);
  };

  return (
    <Item
      onClick={onSelect}
      onDragOver={handleDragOver}
      onDrop={handleDropOnResource}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      className={`
        rounded-full px-4 py-2 cursor-pointer flex items-center justify-between transition-all duration-200 border
        ${
          isSelected
            ? 'bg-red-50 border-red-500 border-2 shadow-md ring-1 ring-red-200'
            : 'bg-white border-gray-200 hover:bg-gray-200 hover:border-gray-400'
        }
        ${isDragOver ? 'ring-1 ring-yellow-300 bg-yellow-50' : ''}
      `}
    >
      <ItemContent>
        <div className="flex items-center gap-2">
          <ItemTitle
            className={`text-sm font-medium ${isSelected ? 'text-red-700' : ''}`}
          >
            {resource.name}
          </ItemTitle>
          <span className="text-xs text-gray-500">#{resource.id}</span>
        </div>
      </ItemContent>

      <div className="flex items-center gap-1.5">
        {(() => {
          const { Icon, color } = getBatteryIconAndColor(
            resource.batteryCount,
            resource.batteryCapacity
          );
          return <Icon className={`h-4 w-4 ${color}`} />;
        })()}
        <span className={`text-xs text-gray-400`}>{resource.batteryCount}</span>
      </div>
    </Item>
  );
}
