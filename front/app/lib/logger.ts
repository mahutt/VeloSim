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
import { TOKEN_STORAGE_KEY } from '~/constants';

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
}

// Define the structure of a log entry as the backend logs/frontend endpoint expects.
interface LogEntry {
  message: string;
  timestamp: string;
  level?: LogLevel;
  stack?: string;
  context?: string;
  userAgent?: string;
  url?: string;
  entityType?: string;
  entityId?: number;
  errorType?: string;
}

// Define the structure of a log entry as the frontend log function accepts
export interface PartialLogEntry {
  message: string;
  level?: LogLevel;
  stack?: string;
  context?: string;
  entityType?: string;
  entityId?: number;
  errorType?: string;
}

/**
 * Adds a timestamp, user agent, and url to the log param to create a valid log entry.
 *
 * @param entry partial log entry with missing metadata
 * @returns Log entry with metadata added
 */
function addMetadataToPartialLogEntry(entry: PartialLogEntry): LogEntry {
  return {
    ...entry,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href,
  };
}

/**
 * Logs an entry to the backend logging system.
 * This should only be called when the user is authenticated.
 * This should only be used for logging frontend-only errors and activity,
 * not for events that make use of a backend endpoint as this is already logged there.
 *
 * @param entry with optional timestamp for convenience
 * @returns void
 */
export async function log(entry: PartialLogEntry) {
  // Only log if user is authenticated
  if (!sessionStorage.getItem(TOKEN_STORAGE_KEY)) {
    console.warn('Attempted to log without authentication.');
    return;
  }
  const completeLogEntry = addMetadataToPartialLogEntry(entry);
  try {
    await api.post('/logs/frontend', completeLogEntry);
  } catch (e) {
    console.error('Failed to send log to backend:', e);
  }
}
