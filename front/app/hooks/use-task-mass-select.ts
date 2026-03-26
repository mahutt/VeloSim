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
  // Tracks selection order so deselecting the anchor rolls back to the previous one
  const anchorStackRef = useRef<number[]>([]);
  const shiftBaseRef = useRef<Set<number>>(new Set());
  const isShiftSequenceRef = useRef(false);
  const isDragSelectingRef = useRef(false);
  const dragSelectStartRef = useRef<number | null>(null);
  const dragBaseSelectionRef = useRef<Set<number>>(new Set());

  const anchor = () =>
    anchorStackRef.current[anchorStackRef.current.length - 1] ?? null;

  const pushAnchor = (taskId: number) => {
    anchorStackRef.current = [
      ...anchorStackRef.current.filter((id) => id !== taskId),
      taskId,
    ];
  };

  const removeAnchor = (taskId: number) => {
    anchorStackRef.current = anchorStackRef.current.filter(
      (id) => id !== taskId
    );
  };

  const resetAnchor = (taskId: number | null = null) => {
    anchorStackRef.current = taskId !== null ? [taskId] : [];
  };

  useEffect(() => {
    setSelectedTaskIds([]);
    resetAnchor();
  }, [reset]);

  useEffect(() => {
    const endDragSelect = () => {
      isDragSelectingRef.current = false;
    };
    window.addEventListener('mouseup', endDragSelect);
    return () => window.removeEventListener('mouseup', endDragSelect);
  }, []);

  const updateSelection = useCallback(
    (nextIds: Set<number>) => {
      const ordered = taskIds.filter((id) => nextIds.has(id));
      setSelectedTaskIds(ordered);
    },
    [taskIds]
  );

  const handleTaskSelect = useCallback(
    (taskId: number, taskIndex: number, event: MouseEvent<HTMLDivElement>) => {
      if (event.shiftKey && anchor() !== null) {
        const currentAnchor = anchor()!;
        const lastIndex = taskIds.indexOf(currentAnchor);
        if (lastIndex !== -1) {
          if (!isShiftSequenceRef.current) {
            shiftBaseRef.current = new Set(selectedTaskIds);
            isShiftSequenceRef.current = true;
          }
          const start = Math.min(lastIndex, taskIndex);
          const end = Math.max(lastIndex, taskIndex);
          const rangeIds = taskIds.slice(start, end + 1);
          updateSelection(new Set([...shiftBaseRef.current, ...rangeIds]));
        }
        return;
      }

      isShiftSequenceRef.current = false;

      if (event.metaKey || event.ctrlKey) {
        const nextIds = new Set(selectedTaskIds);
        if (nextIds.has(taskId)) {
          nextIds.delete(taskId);
          removeAnchor(taskId);
        } else {
          nextIds.add(taskId);
          pushAnchor(taskId);
        }
        updateSelection(nextIds);
        return;
      }

      if (selectedTaskIds.length === 1 && selectedTaskIds[0] === taskId) {
        updateSelection(new Set());
        resetAnchor();
        return;
      }

      updateSelection(new Set([taskId]));
      resetAnchor(taskId);
    },
    [selectedTaskIds, taskIds, updateSelection]
  );

  const selectForDrag = useCallback(
    (taskId: number) => {
      isShiftSequenceRef.current = false;
      if (!selectedTaskIds.includes(taskId)) {
        updateSelection(new Set([taskId]));
        resetAnchor(taskId);
      }
    },
    [selectedTaskIds, updateSelection]
  );

  const startDragSelect = useCallback(
    (taskId: number, ctrlKey: boolean) => {
      isShiftSequenceRef.current = false;
      isDragSelectingRef.current = true;
      dragSelectStartRef.current = taskId;
      if (ctrlKey) {
        dragBaseSelectionRef.current = new Set(selectedTaskIds);
        const toggled = new Set(selectedTaskIds);
        if (toggled.has(taskId)) {
          toggled.delete(taskId);
        } else {
          toggled.add(taskId);
        }
        updateSelection(toggled);
      } else {
        dragBaseSelectionRef.current = new Set();
        updateSelection(new Set([taskId]));
      }
      resetAnchor(taskId);
    },
    [selectedTaskIds, updateSelection]
  );

  const dragSelectEnter = useCallback(
    (taskId: number) => {
      if (!isDragSelectingRef.current || dragSelectStartRef.current === null)
        return;
      const startIndex = taskIds.indexOf(dragSelectStartRef.current);
      const currentIndex = taskIds.indexOf(taskId);
      if (startIndex === -1 || currentIndex === -1) return;
      const start = Math.min(startIndex, currentIndex);
      const end = Math.max(startIndex, currentIndex);
      const rangeIds = taskIds.slice(start, end + 1);
      const result = new Set(dragBaseSelectionRef.current);
      for (const id of rangeIds) {
        if (result.has(id)) {
          result.delete(id);
        } else {
          result.add(id);
        }
      }
      updateSelection(result);
    },
    [taskIds, updateSelection]
  );

  const clearSelection = useCallback(() => {
    updateSelection(new Set());
    resetAnchor();
  }, [updateSelection]);

  return {
    selectedTaskIds,
    isDragSelecting: isDragSelectingRef,
    handleTaskSelect,
    selectForDrag,
    startDragSelect,
    dragSelectEnter,
    clearSelection,
  };
}
