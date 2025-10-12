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

const API_BASE_URL = 'http://localhost:8000/api/v1';
const WS_BASE_URL = 'ws://localhost:8000/api/v1';

/**
 * Connect to simulation frame stream
 * @param simId - The simulation ID to connect to
 * @returns WebSocket instance
 */
export function connectToFrameStream(simId: string): WebSocket {
  const wsUrl = `${WS_BASE_URL}/simulation/stream/${simId}`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log(`Connected to simulation ${simId} frame stream`);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = (event) => {
    console.log(`WebSocket closed for sim ${simId}:`, event.code, event.reason);
  };

  return ws;
}

/**
 * Start a new simulation
 */
export async function startSimulation(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/simulation/start`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to start simulation');
  }

  const data = await response.json();
  return data.sim_id;
}

/**
 * Stop a simulation
 */
export async function stopSimulation(simId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/simulation/stop/${simId}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to stop simulation');
  }
}

/**
 * Get list of active simulations
 */
export async function listSimulations(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/simulation/list`);

  if (!response.ok) {
    throw new Error('Failed to list simulations');
  }

  const data = await response.json();
  return data.active_simulations;
}
