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

import api from '~/api';
import type { Speed } from '~/providers/simulation-provider';
import type { BackendPayload } from '~/types';
import {
  logFrameProcessingError,
  logSimulationError,
} from '~/utils/simulation-error-utils';
import type FrameSource from './frame-source';

export class ServerFrameSource implements FrameSource {
  private simulationId: string;
  private onFrame: (frame: BackendPayload) => void;
  private onError: (title: string, message: string) => void;

  private wsUrl: string | null;
  private ws: WebSocket | null;
  private isRunning: Promise<boolean>;
  private resolveIsRunning!: (value: boolean) => void;
  private rejectIsRunning!: (reason?: Error) => void;
  private speed: Speed;

  constructor(
    simulationId: string,
    onFrame: (frame: BackendPayload) => void,
    onError: (title: string, message: string) => void
  ) {
    this.simulationId = simulationId;
    this.onFrame = onFrame;
    this.onError = onError;

    this.wsUrl = null;
    this.ws = null;
    this.isRunning = new Promise<boolean>((resolve, reject) => {
      this.resolveIsRunning = resolve;
      this.rejectIsRunning = reject;
    });

    this.speed = 1;
  }

  private static buildWebSocketUrl(simulationId: string): string {
    const apiBaseUrl = import.meta.env.VITE_BACKEND_URL;
    const url = apiBaseUrl ? new URL(apiBaseUrl) : null;
    const wsProtocol =
      url?.protocol === 'https:' || window.location.protocol === 'https:'
        ? 'wss:'
        : 'ws:';
    const wsHost = url?.host || window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/simulation/stream/${simulationId}`;
    return wsUrl;
  }

  public async start(): Promise<boolean> {
    //
    this.wsUrl = ServerFrameSource.buildWebSocketUrl(this.simulationId);
    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      console.log('[WS] ✅ Connection opened');
      // setConnectionAttempts(0);
    };

    this.ws.onmessage = (event) => {
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
          this.rejectIsRunning(
            new Error(message.message || 'Simulation error')
          );
          this.onError(
            'Simulation Error',
            message.message || 'An error occurred'
          );
          return;
        }

        // Parse payload if it's a string
        let payload = message.payload;
        if (typeof payload === 'string') {
          payload = JSON.parse(payload);
        }

        // Assume this message is a frame
        // Resolve the isRunning promise
        this.resolveIsRunning(true);

        // Handle initial frame (seq === 0)
        if (message.seq === 0) {
          console.log('[WS] 🎬 Initial frame received');
          try {
            this.onFrame(payload);
          } catch (error) {
            logSimulationError(error, 'Failed to process initial frame', {
              errorType: 'INITIAL_FRAME_ERROR',
              payloadKeys: Object.keys(payload),
            });
            this.onError(
              'Initialization Error',
              'Failed to initialize simulation. Please refresh and try again.'
            );
          }
          return;
        }

        // Handle regular frames (seq > 0)
        if (message.seq > 0) {
          console.log('[WS] 🎞️  Frame', message.seq);
          try {
            this.onFrame(payload);
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
        this.onError(
          'Simulation Frame Error',
          'An error occurred while processing simulation data. The simulation may not display correctly.'
        );
      }
    };

    this.ws.onerror = (event) => {
      console.error('[WS] ❌ WebSocket error:', event);

      logSimulationError(
        new Error('WebSocket connection failed'),
        'WebSocket connection error',
        {
          errorType: 'WEBSOCKET_ERROR',
          simId: this.simulationId,
          wsUrl: this.wsUrl,
          readyState:
            (['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'] as const)[
              this.ws?.readyState ?? -1
            ] ?? 'UNKNOWN',
        }
      );

      this.onError(
        'Connection Error',
        'Failed to connect to simulation. Check authentication and try again.'
      );
    };

    this.ws.onclose = (event) => {
      console.log('[WS] 🔌 Connection closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });

      // Pause the simulation by setting playback speed to 0
      api
        .post(`/simulation/${this.simulationId}/playbackSpeed`, {
          playback_speed: 0,
        })
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
            simId: this.simulationId,
            closeCode: event.code,
            closeReason: event.reason,
          }
        );

        this.onError(
          'Authentication Failed',
          'WebSocket authentication failed. Please try logging in again.'
        );
        return;
      }
    };
    return this.isRunning;
  }

  public stop() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }

  public async setSpeed(speed: Speed): Promise<void> {
    if (this.speed === speed) return;
    await api.post(`/simulation/${this.simulationId}/playbackSpeed`, {
      playback_speed: speed,
    });
    this.speed = speed;
  }
}
