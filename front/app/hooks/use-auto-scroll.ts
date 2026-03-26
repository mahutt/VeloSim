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

import { useCallback, useEffect, useRef } from 'react';

const EDGE_THRESHOLD = 30;
const SCROLL_SPEED = 4;

export function useAutoScroll(isDragSelecting: React.RefObject<boolean>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  const directionRef = useRef<number>(0);
  const viewportRef = useRef<HTMLElement | null>(null);

  const getViewport = useCallback(() => {
    if (!viewportRef.current?.isConnected) {
      viewportRef.current = containerRef.current?.closest(
        '[data-slot="scroll-area-viewport"]'
      ) as HTMLElement | null;
    }
    return viewportRef.current;
  }, []);

  const tick = useCallback(() => {
    if (!isDragSelecting.current || directionRef.current === 0) {
      rafRef.current = null;
      return;
    }
    const viewport = getViewport();
    if (viewport) viewport.scrollTop += directionRef.current * SCROLL_SPEED;
    rafRef.current = requestAnimationFrame(tick);
  }, [isDragSelecting, getViewport]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragSelecting.current) return;
      const viewport = getViewport();
      if (!viewport) return;
      const rect = viewport.getBoundingClientRect();
      if (e.clientY - rect.top < EDGE_THRESHOLD) {
        directionRef.current = -1;
      } else if (rect.bottom - e.clientY < EDGE_THRESHOLD) {
        directionRef.current = 1;
      } else {
        directionRef.current = 0;
      }
      if (directionRef.current !== 0 && rafRef.current === null) {
        rafRef.current = requestAnimationFrame(tick);
      }
    },
    [isDragSelecting, getViewport, tick]
  );

  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return { containerRef, handleMouseMove };
}
