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

import type { Resource } from '~/types';

export function ResourceItem({
  resource,
  onSelect,
  isSelected = false,
}: {
  resource?: Resource;
  onSelect: () => void;
  isSelected?: boolean;
}) {
  return (
    <div
      className={`
        rounded-full px-4 py-2 cursor-pointer flex items-center justify-between transition-all duration-200 border
        ${
          isSelected
            ? 'bg-red-50 border-red-500 border-2 shadow-md ring-1 ring-red-200'
            : 'bg-white border-gray-200 hover:bg-gray-200 hover:border-gray-400'
        }
      `}
      onClick={() => onSelect()}
    >
      <div className="flex items-center gap-2">
        <span
          className={`text-sm font-medium ${isSelected ? 'text-red-700' : ''}`}
        >
          {resource ? `#${resource.id}` : ''}
        </span>
      </div>
      <span
        className={`text-xs ${isSelected ? 'text-red-600' : 'text-gray-400'}`}
      >
        {resource ? `${resource.taskList.length} tasks` : ''}
      </span>
    </div>
  );
}
