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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutoScroll } from '~/hooks/use-auto-scroll';

describe('useAutoScroll', () => {
  // Capture the last RAF callback so tests can invoke the tick manually
  let rafCallback: FrameRequestCallback | null = null;
  let rafId = 0;

  beforeEach(() => {
    rafCallback = null;
    rafId = 0;
    vi.stubGlobal(
      'requestAnimationFrame',
      vi.fn((cb: FrameRequestCallback) => {
        rafCallback = cb;
        return ++rafId;
      })
    );
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = '';
  });

  // Viewport rect: top=100, bottom=500. EDGE_THRESHOLD=30.
  // Near-top zone:    clientY < 130  (100 + 30)
  // Near-bottom zone: clientY > 470  (500 - 30)
  // Middle zone:      130 <= clientY <= 470
  const VIEWPORT_RECT = {
    top: 100,
    bottom: 500,
    left: 0,
    right: 300,
    width: 300,
    height: 400,
    x: 0,
    y: 100,
    toJSON: () => ({}),
  } as DOMRect;

  const makeDragSelectingRef = (value: boolean) =>
    ({ current: value }) as React.RefObject<boolean>;

  const makeMouseEvent = (clientY: number) => ({ clientY }) as React.MouseEvent;

  /**
   * Creates a [data-slot="scroll-area-viewport"] element containing a child
   * div, attaches them to document.body, then wires containerRef to the child.
   */
  const setupDOM = (containerRef: React.RefObject<HTMLDivElement | null>) => {
    const viewport = document.createElement('div');
    viewport.setAttribute('data-slot', 'scroll-area-viewport');
    viewport.getBoundingClientRect = vi.fn(() => VIEWPORT_RECT);
    viewport.scrollTop = 0;

    const container = document.createElement('div');
    viewport.appendChild(container);
    document.body.appendChild(viewport);

    // useRef returns a mutable object despite the readonly typing
    (containerRef as { current: HTMLDivElement }).current = container;

    return viewport;
  };

  it('returns containerRef and handleMouseMove', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(false))
    );
    expect(result.current.containerRef).toBeDefined();
    expect(result.current.handleMouseMove).toBeInstanceOf(Function);
  });

  it('does nothing when not drag-selecting', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(false))
    );
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(115)); // near top edge
    });

    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it('starts RAF when mouse is near the top edge during drag', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(115)); // 115-100=15 < 30
    });

    expect(requestAnimationFrame).toHaveBeenCalledTimes(1);
  });

  it('starts RAF when mouse is near the bottom edge during drag', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(480)); // 500-480=20 < 30
    });

    expect(requestAnimationFrame).toHaveBeenCalledTimes(1);
  });

  it('does not start RAF when mouse is in the middle', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(300));
    });

    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });

  it('scrolls up (negative scrollTop delta) when ticking near top edge', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    const viewport = setupDOM(result.current.containerRef);
    viewport.scrollTop = 100;

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(115));
    });
    act(() => {
      rafCallback?.(0); // run the tick
    });

    expect(viewport.scrollTop).toBe(96); // 100 - 4
  });

  it('scrolls down (positive scrollTop delta) when ticking near bottom edge', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    const viewport = setupDOM(result.current.containerRef);
    viewport.scrollTop = 0;

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(480));
    });
    act(() => {
      rafCallback?.(0);
    });

    expect(viewport.scrollTop).toBe(4); // 0 + 4
  });

  it('does not start a second RAF while one is already running', () => {
    const { result } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(115));
      result.current.handleMouseMove(makeMouseEvent(116)); // RAF already pending
    });

    expect(requestAnimationFrame).toHaveBeenCalledTimes(1);
  });

  it('stops the scroll loop when isDragSelecting becomes false', () => {
    const isDragSelecting = makeDragSelectingRef(true);
    const { result } = renderHook(() => useAutoScroll(isDragSelecting));
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(115));
    });

    // Simulate drag end: isDragSelecting flips to false (as use-task-mass-select does on mouseup)
    isDragSelecting.current = false;

    const callsBefore = (requestAnimationFrame as ReturnType<typeof vi.fn>).mock
      .calls.length;

    // Tick fires but isDragSelecting is false, so it should NOT reschedule
    act(() => {
      rafCallback?.(0);
    });

    expect(
      (requestAnimationFrame as ReturnType<typeof vi.fn>).mock.calls.length
    ).toBe(callsBefore);
  });

  it('cancels the pending RAF on unmount', () => {
    const { result, unmount } = renderHook(() =>
      useAutoScroll(makeDragSelectingRef(true))
    );
    setupDOM(result.current.containerRef);

    act(() => {
      result.current.handleMouseMove(makeMouseEvent(115)); // start a loop
    });

    unmount();

    expect(cancelAnimationFrame).toHaveBeenCalled();
  });
});
