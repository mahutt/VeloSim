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

import { useEffect, useRef, useState } from 'react';
import type {
  SimulationStatus,
  UseSimulationWebSocketOptions,
  UseSimulationWebSocketReturn,
} from '~/types';
import {
  logFrameProcessingError,
  logSimulationError,
} from '~/utils/simulation-error-utils';
import api from '~/api';

// WebSocket reconnection settings
const MAX_RETRIES = 5;
const INITIAL_DELAY = 1000; // 1 second

/**
 * Custom hook to manage WebSocket connection for simulation streaming.
 *
 * Handles:
 * - Connection lifecycle (connect, disconnect, reconnect)
 * - Message parsing and routing (initial frame, updates, status, errors)
 * - Reconnection with exponential backoff
 * - Error handling and logging
 *
 * @param options Configuration options for the WebSocket connection
 * @returns Connection state and WebSocket reference
 */
export const useSimulationWebSocket = ({
  simId,
  enabled,
  onInitialFrame,
  onFrameUpdate,
  onError,
}: UseSimulationWebSocketOptions): UseSimulationWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [simulationStatus, setSimulationStatus] =
    useState<SimulationStatus>('idle');
  const [connectionAttempts, setConnectionAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);

  // Store callbacks in refs to avoid recreating WebSocket on callback changes
  const onInitialFrameRef = useRef(onInitialFrame);
  const onFrameUpdateRef = useRef(onFrameUpdate);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onInitialFrameRef.current = onInitialFrame;
    onFrameUpdateRef.current = onFrameUpdate;
    onErrorRef.current = onError;
  }, [onInitialFrame, onFrameUpdate, onError]);

  useEffect(() => {
    if (!enabled || !simId) {
      console.log('[WS] ⏳ Waiting for prerequisites...', {
        enabled,
        simId: !!simId,
      });
      return;
    }

    console.log('[WS] 🚀 Connecting to WebSocket...');

    // Build WebSocket URL
    const apiBaseUrl = import.meta.env.VITE_BACKEND_URL;
    const url = apiBaseUrl ? new URL(apiBaseUrl) : null;
    const wsProtocol =
      url?.protocol === 'https:' || window.location.protocol === 'https:'
        ? 'wss:'
        : 'ws:';
    const wsHost = url?.host || window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/simulation/stream/${simId}`;

    console.log('[WS] URL:', wsUrl);
    console.log('[WS] Cookie will be sent automatically by browser');

    setSimulationStatus('connecting');

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    // ============================================================================
    // WebSocket Event Handlers
    // ============================================================================

    ws.onopen = () => {
      console.log('[WS] ✅ Connection opened');
      setIsConnected(true);
      setConnectionAttempts(0);
      setSimulationStatus('loading');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        // Handle status messages
        if (message.type === 'status') {
          console.log('[WS] 📊 Status:', message.message, message);
          return;
        }

        // Handle error messages
        if (message.type === 'error') {
          console.error('[WS] ❌ Server Error:', message.message);
          onErrorRef.current(
            'Simulation Error',
            message.message || 'An error occurred'
          );
          setSimulationStatus('error');
          return;
        }

        // Parse payload if it's a string
        let payload = message.payload;
        if (typeof payload === 'string') {
          payload = JSON.parse(payload);
        }

        // Handle initial frame (seq === 0)
        if (message.seq === 0) {
          console.log('[WS] 🎬 Initial frame received');
          try {
            onInitialFrameRef.current(payload);
            setSimulationStatus('ready');
          } catch (error) {
            logSimulationError(error, 'Failed to process initial frame', {
              errorType: 'INITIAL_FRAME_ERROR',
              payloadKeys: Object.keys(payload),
            });
            onErrorRef.current(
              'Initialization Error',
              'Failed to initialize simulation. Please refresh and try again.'
            );
            setSimulationStatus('error');
          }
          return;
        }

        // Handle regular frames (seq > 0)
        if (message.seq > 0) {
          console.log('[WS] 🎞️  Frame', message.seq);
          try {
            onFrameUpdateRef.current(payload);
            setSimulationStatus((prev) =>
              prev !== 'running' ? 'running' : prev
            );
          } catch (error) {
            logSimulationError(error, 'Failed to process frame update', {
              errorType: 'FRAME_UPDATE_ERROR',
              payloadKeys: Object.keys(payload),
            });
            // Don't show error dialog for individual frame failures - just log it
          }
          return;
        }

        console.warn('[WS] ⚠️  Unknown message:', message);
      } catch (error) {
        console.error('[WS] ❌ Parse error:', error);
        console.error('[WS] Raw data:', event.data);
        logFrameProcessingError(error, event.data?.seq || -1);
        onErrorRef.current(
          'Simulation Frame Error',
          'An error occurred while processing simulation data. The simulation may not display correctly.'
        );
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] ❌ WebSocket error:', error);

      logSimulationError(error, 'WebSocket connection error', {
        errorType: 'WEBSOCKET_ERROR',
        simId,
        wsUrl,
      });

      onErrorRef.current(
        'Connection Error',
        'Failed to connect to simulation. Check authentication and try again.'
      );
      setSimulationStatus('error');
    };

    ws.onclose = (event) => {
      console.log('[WS] 🔌 Connection closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });

      setIsConnected(false);

      // Pause the simulation by setting playback speed to 0
      api
        .post(`/simulation/${simId}/playbackSpeed`, { playback_speed: 0 })
        .then(() => {
          console.log('[WS] ⏸️  Playback paused on disconnect');
        })
        .catch((error) => {
          console.error('[WS] Failed to pause playback:', error);
        });

      // Code 1008 = Policy Violation (auth failure)
      if (event.code === 1008) {
        console.error('[WS] ❌ Authentication failed (code 1008)');

        logSimulationError(
          new Error('WebSocket authentication failed'),
          'WebSocket closed due to authentication failure',
          {
            errorType: 'WEBSOCKET_AUTH_FAILURE',
            simId,
            closeCode: event.code,
            closeReason: event.reason,
          }
        );

        onErrorRef.current(
          'Authentication Failed',
          'WebSocket authentication failed. Please try logging in again.'
        );
        setSimulationStatus('error');
        return;
      }

      setSimulationStatus((prev) => (prev !== 'error' ? 'idle' : prev));

      // Retry logic for network errors
      if (connectionAttempts < MAX_RETRIES && event.code === 1006) {
        const delay = INITIAL_DELAY * Math.pow(2, connectionAttempts);
        console.log(
          `[WS] 🔄 Retry ${connectionAttempts + 1}/${MAX_RETRIES} in ${delay}ms`
        );

        setTimeout(() => {
          setConnectionAttempts((prev) => prev + 1);
        }, delay);
      }
    };

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [enabled, simId, connectionAttempts]);

  return {
    isConnected,
    simulationStatus,
    wsRef,
  };
};
