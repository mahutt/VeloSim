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

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTaskMassSelect } from '~/hooks/use-task-mass-select';

const makeEvent = (
  options: Partial<{
    shiftKey: boolean;
    metaKey: boolean;
    ctrlKey: boolean;
  }> = {}
) =>
  ({
    shiftKey: options.shiftKey ?? false,
    metaKey: options.metaKey ?? false,
    ctrlKey: options.ctrlKey ?? false,
  }) as unknown as React.MouseEvent<HTMLDivElement>;

describe('useTaskMassSelect', () => {
  const taskIds = [10, 11, 12, 13];

  it('selects a single task on click', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
    });

    expect(result.current.selectedTaskIds).toEqual([11]);
  });

  it('selects a contiguous range with shift click', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
      result.current.handleTaskSelect(12, 2, makeEvent({ shiftKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([10, 11, 12]);
  });

  it('shift click after ctrl click adds range without removing existing selection', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });
    act(() => {
      result.current.handleTaskSelect(13, 3, makeEvent({ ctrlKey: true }));
    });
    // Shift+click from anchor (13) to 11 — should add [11,12,13] to [10,13]
    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent({ shiftKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([10, 11, 12, 13]);
  });

  it('consecutive shift clicks replace previous range without accumulating', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });
    act(() => {
      result.current.handleTaskSelect(13, 3, makeEvent({ ctrlKey: true }));
    });
    // First shift: base=[10,13], anchor=13, range [11..13] → [10,11,12,13]
    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent({ shiftKey: true }));
    });
    expect(result.current.selectedTaskIds).toEqual([10, 11, 12, 13]);

    // Second shift: same base=[10,13], anchor=13, range [12..13] → [10,12,13] (not [10,11,12,13])
    act(() => {
      result.current.handleTaskSelect(12, 2, makeEvent({ shiftKey: true }));
    });
    expect(result.current.selectedTaskIds).toEqual([10, 12, 13]);
  });

  it('toggles selection with meta/ctrl click', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });

    expect(result.current.selectedTaskIds).toEqual([10]);

    act(() => {
      result.current.handleTaskSelect(12, 2, makeEvent({ metaKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([10, 12]);

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent({ ctrlKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([12]);
  });

  it('rolls back anchor to previous selected task when ctrl+deselecting the anchor', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });
    act(() => {
      result.current.handleTaskSelect(12, 2, makeEvent({ ctrlKey: true }));
    });
    // Deselect 12 (the current anchor) — anchor should roll back to 10
    act(() => {
      result.current.handleTaskSelect(12, 2, makeEvent({ ctrlKey: true }));
    });
    // Shift+click from rolled-back anchor (10) to 13 → [10, 11, 12, 13]
    act(() => {
      result.current.handleTaskSelect(13, 3, makeEvent({ shiftKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([10, 11, 12, 13]);
  });

  it('clears selection when clicking the only selected task', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
    });

    expect(result.current.selectedTaskIds).toEqual([11]);

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
    });

    expect(result.current.selectedTaskIds).toEqual([]);
  });

  it('selects dragged task if not already selected', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
      result.current.selectForDrag(12);
    });

    expect(result.current.selectedTaskIds).toEqual([12]);
  });

  it('keeps selection when dragging an already selected task', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
      result.current.selectForDrag(11);
    });

    expect(result.current.selectedTaskIds).toEqual([11]);
  });

  it('right-click drag selects a range', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.startDragSelect(10, false);
    });

    expect(result.current.selectedTaskIds).toEqual([10]);

    act(() => {
      result.current.dragSelectEnter(12);
    });

    expect(result.current.selectedTaskIds).toEqual([10, 11, 12]);

    act(() => {
      result.current.dragSelectEnter(11);
    });

    expect(result.current.selectedTaskIds).toEqual([10, 11]);
  });

  it('right-click drag with ctrl toggles range against base selection', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });
    act(() => {
      result.current.handleTaskSelect(13, 3, makeEvent({ metaKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([10, 13]);

    act(() => {
      result.current.startDragSelect(11, true);
    });

    // 11 toggled in (base={10,13}) → {10,11,13}
    expect(result.current.selectedTaskIds).toEqual([10, 11, 13]);

    act(() => {
      result.current.dragSelectEnter(12);
    });

    // range [11,12] toggled against base {10,13} → {10,11,12,13}
    expect(result.current.selectedTaskIds).toEqual([10, 11, 12, 13]);

    act(() => {
      result.current.dragSelectEnter(13);
    });

    // range [11,13] toggled against base {10,13}: 11→add, 12→add, 13→remove → {10,11,12}
    expect(result.current.selectedTaskIds).toEqual([10, 11, 12]);
  });

  it('drag select does nothing after mouseup', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.startDragSelect(10, false);
    });

    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });

    act(() => {
      result.current.dragSelectEnter(12);
    });

    expect(result.current.selectedTaskIds).toEqual([10]);
  });

  it('resets selection when reset value changes', () => {
    const { result, rerender } = renderHook(
      ({ ids, reset }) => useTaskMassSelect(ids, reset),
      {
        initialProps: { ids: taskIds, reset: 'a' },
      }
    );

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });

    expect(result.current.selectedTaskIds).toEqual([10]);

    rerender({ ids: taskIds, reset: 'b' });

    expect(result.current.selectedTaskIds).toEqual([]);
  });

  it('plain right-click drag replaces prior selection', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });
    act(() => {
      result.current.handleTaskSelect(13, 3, makeEvent({ metaKey: true }));
    });

    expect(result.current.selectedTaskIds).toEqual([10, 13]);

    act(() => {
      result.current.startDragSelect(11, false);
    });

    expect(result.current.selectedTaskIds).toEqual([11]);
  });

  it('ctrl right-click drag on selected task deselects it', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
    });

    expect(result.current.selectedTaskIds).toEqual([11]);

    act(() => {
      result.current.startDragSelect(11, true);
    });

    expect(result.current.selectedTaskIds).toEqual([]);
  });

  it('dragSelectEnter is a no-op when not drag-selecting', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(10, 0, makeEvent());
    });

    act(() => {
      result.current.dragSelectEnter(12);
    });

    expect(result.current.selectedTaskIds).toEqual([10]);
  });
});
