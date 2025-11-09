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

import { log, LogLevel } from '~/lib/logger';

/**
 * Represents the three states of simulation data:
 * - Server: Simulation state in memory on the server
 * - Frontend: Simulation state in memory on the browser
 * - Mapbox: Partial representation of state managed by mapbox-gl
 */
export enum SimulationStateLayer {
  Server = 'server',
  Frontend = 'frontend',
  Mapbox = 'mapbox',
}

/**
 * Logs an error for debugging and monitoring.
 * This logs to console with structured data that can be picked up by logging systems like Grafana.
 * Also sends the error to the backend logging endpoint.
 *
 * @param error Error object or string
 * @param context Optional context info (e.g., where the error happened)
 * @param additionalData Optional additional data to log
 */
export function logSimulationError(
  error: unknown,
  context?: string,
  additionalData?: Record<string, unknown>
) {
  const errorMessage = error instanceof Error ? error.message : String(error);
  const errorData = {
    message: errorMessage,
    level: LogLevel.ERROR,
    stack: error instanceof Error ? error.stack : undefined,
    context,
    ...additionalData,
  };

  // Log structured error data to console (Grafana/Loki can scrape these logs)
  // Use try-catch to handle circular references
  try {
    console.error('[SIMULATION_ERROR]', JSON.stringify(errorData, null, 2));
  } catch {
    // Fallback for circular references - log without stringification
    console.error('[SIMULATION_ERROR]', {
      message: errorMessage,
      context,
      note: 'Additional data contained circular references and was omitted',
    });
  }

  // Send to backend logging system
  log(errorData);
}

/**
 * Logs simulation errors with standardized context and additional data.
 * This is a higher-level wrapper around logSimulationError for common simulation scenarios.
 *
 * @param error Error object or string
 * @param context Technical context for logging
 * @param additionalData Optional additional data to log
 */
export function logSimulationErrorWithContext(
  error: unknown,
  context: string,
  additionalData?: Record<string, unknown>
): void {
  logSimulationError(error, context, additionalData);
}

/**
 * Logs a missing entity data error specifically.
 * This is called when a marker is clicked but the entity data doesn't exist.
 * This indicates a state synchronization issue between Frontend and Mapbox layers.
 *
 * @param entityType Type of entity (e.g., "station", "resource")
 * @param entityId ID of the entity
 */
export function logMissingEntityError(
  entityType: string,
  entityId: number
): void {
  const context = `State sync issue: ${entityType} exists in ${SimulationStateLayer.Mapbox} but not in ${SimulationStateLayer.Frontend}`;
  const error = new Error(
    `${entityType} with ID ${entityId} not found in frontend state`
  );

  // Log the error with structured data
  logSimulationError(error, context, {
    entityType,
    entityId,
    errorType: 'MISSING_ENTITY_DATA',
    stateLayer: SimulationStateLayer.Frontend,
    expectedLayer: SimulationStateLayer.Mapbox,
  });
}

/**
 * Logs WebSocket frame processing errors.
 * This is called when there's an issue processing simulation frames from the server.
 *
 * @param error Error object
 * @param frameNumber Frame sequence number
 */
export function logFrameProcessingError(
  error: unknown,
  frameNumber: number
): void {
  logSimulationError(error, 'WebSocket frame processing', {
    frameNumber,
    errorType: 'FRAME_PROCESSING_ERROR',
    stateLayer: SimulationStateLayer.Frontend,
  });
}

/**
 * Logs state synchronization errors between different layers.
 * This is called when there's a mismatch between server, frontend, and mapbox states.
 *
 * @param error Error object
 * @param sourceLayer The layer where the error originated
 * @param targetLayer The layer that was expected to have the data
 */
export function logStateSyncError(
  error: unknown,
  sourceLayer: SimulationStateLayer,
  targetLayer: SimulationStateLayer
): void {
  logSimulationError(
    error,
    `State sync between ${sourceLayer} and ${targetLayer}`,
    {
      errorType: 'STATE_SYNC_ERROR',
      sourceLayer,
      targetLayer,
    }
  );
}
