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
      result.current.selectForDrag(12, 2);
    });

    expect(result.current.selectedTaskIds).toEqual([12]);
  });

  it('keeps selection when dragging an already selected task', () => {
    const { result } = renderHook(() => useTaskMassSelect(taskIds, 'reset'));

    act(() => {
      result.current.handleTaskSelect(11, 1, makeEvent());
      result.current.selectForDrag(11, 1);
    });

    expect(result.current.selectedTaskIds).toEqual([11]);
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
});
