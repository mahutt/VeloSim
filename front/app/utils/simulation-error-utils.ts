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
 * Logs an error for debugging and monitoring.
 * This logs to console with structured data that can be picked up by logging systems like Grafana.
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
  console.error('[SIMULATION_ERROR]', JSON.stringify(errorData, null, 2));
  log(errorData);
}

/**
 * Logs a missing entity data error specifically.
 * This is called when a marker is clicked but the entity data doesn't exist.
 *
 * @param entityType Type of entity (e.g., "station", "resource")
 * @param entityId ID of the entity
 */
export function logMissingEntityError(
  entityType: string,
  entityId: number
): void {
  const context = `Missing ${entityType} data`;
  const error = new Error(
    `${entityType} with ID ${entityId} not found in state`
  );

  // Log the error with structured data
  logSimulationError(error, context, {
    entityType,
    entityId,
    errorType: 'MISSING_ENTITY_DATA',
  });
}
