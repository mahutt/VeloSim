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

import { useEffect, useState, useRef, useCallback } from 'react';
import type { SimulationFrame } from '../types';
import { connectToFrameStream } from '../lib/websocket-frame-stream';

/**
 * React Hook for managing simulation frame stream
 *
 * @param simId - Simulation ID to connect to (null = don't connect)
 * @returns Object with frames, connection status, and control functions
 *
 * @example
 * ```tsx
 * const { frames, connected, error, clearFrames } = useSimulationFrames(simId);
 *
 * return (
 *   <div>
 *     <p>Status: {connected ? 'Connected' : 'Disconnected'}</p>
 *     <p>Frames: {frames.length}</p>
 *     {error && <p>Error: {error}</p>}
 *   </div>
 * );
 * ```
 */
export function useSimulationFrames(simId: string | null) {
  const [frames, setFrames] = useState<SimulationFrame[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const clearFrames = useCallback(() => {
    setFrames([]);
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!simId) {
      setConnected(false);
      return;
    }

    const ws = connectToFrameStream(simId);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
      setConnected(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle connection confirmation
        if (data.type === 'connection_established') {
          console.log('Connection established:', data.message);
          return;
        }

        // Handle error messages
        if (data.error) {
          setError(data.error);
          return;
        }

        // Handle ping/pong
        if (data.type === 'pong') {
          return;
        }

        // It's a frame update
        if (data.sim_id && data.seq_numb !== undefined) {
          setFrames((prev) => [...prev, data as SimulationFrame]);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
        setError('Failed to parse frame data');
      }
    };

    // Send periodic pings to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000); // Every 30 seconds

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [simId]);

  return {
    frames,
    connected,
    error,
    clearFrames,
    disconnect,
  };
}
