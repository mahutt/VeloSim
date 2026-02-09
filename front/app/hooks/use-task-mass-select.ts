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
  useCallback,
  useEffect,
  useRef,
  useState,
  type MouseEvent,
} from 'react';

export function useTaskMassSelect(taskIds: number[], reset: number | string) {
  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>([]);
  const lastSelectedTaskRef = useRef<number | null>(null);

  useEffect(() => {
    setSelectedTaskIds([]);
    lastSelectedTaskRef.current = null;
  }, [reset]);

  const updateSelection = useCallback(
    (nextIds: Set<number>) => {
      const ordered = taskIds.filter((id) => nextIds.has(id));
      setSelectedTaskIds(ordered);
    },
    [taskIds]
  );

  const handleTaskSelect = useCallback(
    (taskId: number, taskIndex: number, event: MouseEvent<HTMLDivElement>) => {
      if (event.shiftKey && lastSelectedTaskRef.current !== null) {
        const start = Math.min(lastSelectedTaskRef.current, taskIndex);
        const end = Math.max(lastSelectedTaskRef.current, taskIndex);
        const rangeIds = taskIds.slice(start, end + 1);
        updateSelection(new Set(rangeIds));
        return;
      }

      if (event.metaKey || event.ctrlKey) {
        const nextIds = new Set(selectedTaskIds);
        if (nextIds.has(taskId)) {
          nextIds.delete(taskId);
        } else {
          nextIds.add(taskId);
        }
        updateSelection(nextIds);
        lastSelectedTaskRef.current = taskIndex;
        return;
      }

      if (selectedTaskIds.length === 1 && selectedTaskIds[0] === taskId) {
        updateSelection(new Set());
        lastSelectedTaskRef.current = null;
        return;
      }

      updateSelection(new Set([taskId]));
      lastSelectedTaskRef.current = taskIndex;
    },
    [selectedTaskIds, taskIds, updateSelection]
  );

  const selectForDrag = useCallback(
    (taskId: number, taskIndex: number) => {
      if (!selectedTaskIds.includes(taskId)) {
        updateSelection(new Set([taskId]));
        lastSelectedTaskRef.current = taskIndex;
      }
    },
    [selectedTaskIds, updateSelection]
  );

  return {
    selectedTaskIds,
    handleTaskSelect,
    selectForDrag,
  };
}
