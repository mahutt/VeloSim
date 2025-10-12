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

import { useState, useCallback } from 'react';
import { startSimulation, stopSimulation } from '../lib/websocket-frame-stream';

/**
 * React Hook for managing simulation lifecycle (start/stop)
 *
 * @example
 * ```tsx
 * const { simId, isRunning, start, stop } = useSimulationLifecycle();
 *
 * return (
 *   <button onClick={isRunning ? stop : start}>
 *     {isRunning ? 'Stop' : 'Start'} Simulation
 *   </button>
 * );
 * ```
 */
export function useSimulationLifecycle() {
  const [simId, setSimId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async () => {
    try {
      setError(null);
      const id = await startSimulation();
      setSimId(id);
      setIsRunning(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to start simulation'
      );
      console.error('Failed to start simulation:', err);
    }
  }, []);

  const stop = useCallback(async () => {
    if (!simId) return;

    try {
      setError(null);
      await stopSimulation(simId);
      setIsRunning(false);
      setSimId(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to stop simulation'
      );
      console.error('Failed to stop simulation:', err);
    }
  }, [simId]);

  return {
    simId,
    isRunning,
    error,
    start,
    stop,
  };
}
