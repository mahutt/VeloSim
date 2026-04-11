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
import type { TranslationSchema } from '~/lib/i18n';
import type { GetSimulationReportResponse } from '~/types';

/**
 * Canonical empty report shape used when backend values are unavailable.
 *
 * Contract: mirrors `GetSimulationReportResponse` from `~/types`.
 */
export const DEFAULT_SIMULATION_REPORT: GetSimulationReportResponse = {
  servicingToDrivingRatio: null,
  vehicleUtilizationRatio: null,
  averageTasksServicedPerShift: null,
  averageTaskResponseTime: null,
  vehicleDistanceTraveled: null,
};

/**
 * Ordered report metric keys used by both:
 * 1) summary text rendering and
 * 2) CSV export columns.
 *
 * Assumption: this order is a product-level display/export contract.
 */
export const SIMULATION_REPORT_METRIC_KEYS: Array<
  keyof GetSimulationReportResponse
> = [
  'servicingToDrivingRatio',
  'vehicleUtilizationRatio',
  'averageTasksServicedPerShift',
  'averageTaskResponseTime',
  'vehicleDistanceTraveled',
];

/**
 * Translation selectors matching `SIMULATION_REPORT_METRIC_KEYS` by index.
 *
 * This keeps i18n access fully typed/direct while still
 * allowing indexed iteration over metric metadata.
 */
export const SIMULATION_REPORT_SUMMARY_LEGEND_SELECTORS = [
  (t: TranslationSchema) => t.simulations.report.legend.servicingToDrivingRatio,
  (t: TranslationSchema) => t.simulations.report.legend.vehicleUtilizationRatio,
  (t: TranslationSchema) =>
    t.simulations.report.legend.averageTasksServicedPerShift,
  (t: TranslationSchema) => t.simulations.report.legend.averageTaskResponseTime,
  (t: TranslationSchema) =>
    t.simulations.report.legend.totalVehicleDistanceTravelled,
] as const;

/**
 * Backward-compatible static labels used by tests and CSV-adjacent UI assertions.
 * UI rendering should prefer `SIMULATION_REPORT_SUMMARY_LEGEND_SELECTORS` with i18n.
 */
export const SIMULATION_REPORT_SUMMARY_LEGEND = [
  'Servicing to Driving Ratio',
  'Vehicle Utilization Ratio',
  'Average Tasks Serviced Per Shift',
  'Average Task Response Time',
  'Total Vehicle Distance Travelled',
] as const;

type GetSimulationReportOptions = {
  forceRefresh?: boolean;
};

// Module-scoped memoization caches (lifespan = page session).
const simulationReportCache = new Map<string, GetSimulationReportResponse>();
const simulationReportRequestCache = new Map<
  string,
  Promise<GetSimulationReportResponse>
>();

/**
 * Fetches simulation report data from `GET /simulation/{simId}/report`.
 *
 * API contract notes:
 * - backend returns camelCase keys matching `GetSimulationReportResponse`
 * - missing keys are backfilled from `DEFAULT_SIMULATION_REPORT`
 *
 * Caching behavior:
 * - returns cached report when available
 * - de-duplicates concurrent requests for the same simulation id
 * - no explicit invalidation; data is assumed stable enough for this page session
 */
export async function getSimulationReport(
  simId: string,
  options?: GetSimulationReportOptions
): Promise<GetSimulationReportResponse> {
  const forceRefresh = options?.forceRefresh === true;
  if (!forceRefresh) {
    const cached = simulationReportCache.get(simId);
    if (cached) {
      return cached;
    }

    const pendingRequest = simulationReportRequestCache.get(simId);
    if (pendingRequest) {
      return pendingRequest;
    }
  }

  const request = api
    .get<GetSimulationReportResponse>(`/simulation/${simId}/report`)
    .then((response) => {
      const report = { ...DEFAULT_SIMULATION_REPORT, ...response.data };
      simulationReportCache.set(simId, report);
      return report;
    })
    .finally(() => {
      if (simulationReportRequestCache.get(simId) === request) {
        simulationReportRequestCache.delete(simId);
      }
    });

  simulationReportRequestCache.set(simId, request);
  return request;
}

/**
 * Downloads report metrics as CSV (`sim_{simId}.csv`).
 *
 * CSV shape:
 * - header: `SIMULATION_REPORT_METRIC_KEYS`
 * - row: corresponding metric values in the same order
 *
 * Assumption: current values are numeric or empty, so quoting/escaping is not required.
 */
export function downloadSimulationReportCsv(
  simId: string,
  report: GetSimulationReportResponse
): void {
  const header = SIMULATION_REPORT_METRIC_KEYS.join(',');
  const rows = SIMULATION_REPORT_METRIC_KEYS.map(
    (key) => report[key] ?? ''
  ).join(',');

  const csvDataString = [header, rows].join('\n');
  const blob = new Blob([csvDataString], {
    type: 'text/csv;charset=utf-8;',
  });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `sim_${simId}.csv`);
  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
