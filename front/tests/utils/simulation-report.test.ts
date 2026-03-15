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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import api from '~/api';
import type { GetSimulationReportResponse } from '~/types';
import {
  DEFAULT_SIMULATION_REPORT,
  SIMULATION_REPORT_METRIC_KEYS,
  SIMULATION_REPORT_SUMMARY_LEGEND,
  formatSimulationReportMetricValue,
  getSimulationReport,
  downloadSimulationReportCsv,
} from '~/utils/simulation-report';

vi.mock('~/api');

beforeEach(() => {
  vi.resetAllMocks();
});

describe('formatSimulationReportMetricValue', () => {
  it('returns "--" for null', () => {
    expect(formatSimulationReportMetricValue(null)).toBe('--');
  });

  it('trims trailing .00 from whole numbers', () => {
    expect(formatSimulationReportMetricValue(3)).toBe('3');
    expect(formatSimulationReportMetricValue(0)).toBe('0');
    expect(formatSimulationReportMetricValue(100)).toBe('100');
  });

  it('trims trailing zero when only one decimal place is significant', () => {
    expect(formatSimulationReportMetricValue(1.5)).toBe('1.5');
    expect(formatSimulationReportMetricValue(0.8)).toBe('0.8');
  });

  it('keeps both decimal places when both are significant', () => {
    expect(formatSimulationReportMetricValue(1.23)).toBe('1.23');
    expect(formatSimulationReportMetricValue(0.45)).toBe('0.45');
  });
});

describe('DEFAULT_SIMULATION_REPORT', () => {
  it('has null for every key in SIMULATION_REPORT_METRIC_KEYS', () => {
    for (const key of SIMULATION_REPORT_METRIC_KEYS) {
      expect(DEFAULT_SIMULATION_REPORT[key]).toBeNull();
    }
  });
});

describe('SIMULATION_REPORT_METRIC_KEYS and SIMULATION_REPORT_SUMMARY_LEGEND', () => {
  it('have the same length — legend labels align with metric keys', () => {
    expect(SIMULATION_REPORT_METRIC_KEYS.length).toBe(
      SIMULATION_REPORT_SUMMARY_LEGEND.length
    );
  });

  it('SIMULATION_REPORT_METRIC_KEYS covers all keys of DEFAULT_SIMULATION_REPORT', () => {
    const defaultKeys = Object.keys(DEFAULT_SIMULATION_REPORT);
    for (const key of defaultKeys) {
      expect(SIMULATION_REPORT_METRIC_KEYS).toContain(key);
    }
  });
});

describe('getSimulationReport', () => {
  it('calls GET /simulation/{simId}/report with the correct path', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { servicingToDrivingRatio: 1.5 },
    });

    const result = await getSimulationReport('sim-get-1');

    expect(api.get).toHaveBeenCalledWith('/simulation/sim-get-1/report');
    expect(result.servicingToDrivingRatio).toBe(1.5);
  });

  it('fills keys missing from the response with DEFAULT_SIMULATION_REPORT values', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { servicingToDrivingRatio: 2.0 },
    });

    const result = await getSimulationReport('sim-get-2');

    expect(result.vehicleUtilizationRatio).toBeNull();
    expect(result.averageTasksServicedPerShift).toBeNull();
  });

  it('returns the cached result without re-fetching on subsequent calls', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { servicingToDrivingRatio: 0.5 },
    });

    await getSimulationReport('sim-cache-1');
    vi.mocked(api.get).mockClear();

    const cached = await getSimulationReport('sim-cache-1');

    expect(api.get).not.toHaveBeenCalled();
    expect(cached.servicingToDrivingRatio).toBe(0.5);
  });

  it('deduplicates concurrent in-flight requests for the same simulation', async () => {
    let resolve!: (v: unknown) => void;
    vi.mocked(api.get).mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }) as ReturnType<typeof api.get>
    );

    const p1 = getSimulationReport('sim-dedup-1');
    const p2 = getSimulationReport('sim-dedup-1');

    resolve({ data: { servicingToDrivingRatio: 1.0 } });

    const [r1, r2] = await Promise.all([p1, p2]);

    expect(api.get).toHaveBeenCalledTimes(1);
    expect(r1.servicingToDrivingRatio).toBe(1.0);
    expect(r2.servicingToDrivingRatio).toBe(1.0);
  });
});

describe('downloadSimulationReportCsv', () => {
  const origCreateObjectURL = URL.createObjectURL;
  const origRevokeObjectURL = URL.revokeObjectURL;

  afterEach(() => {
    vi.unstubAllGlobals();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: origCreateObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: origRevokeObjectURL,
    });
    vi.restoreAllMocks();
  });

  function setupDownloadMocks() {
    const blobParts: string[] = [];
    vi.stubGlobal(
      'Blob',
      class {
        constructor(parts: BlobPart[]) {
          for (const p of parts) {
            if (typeof p === 'string') blobParts.push(p);
          }
        }
      }
    );

    const createObjectURL = vi.fn(() => 'blob:test-url');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      writable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      writable: true,
      value: revokeObjectURL,
    });

    const link = document.createElement('a');
    const clickSpy = vi.spyOn(link, 'click').mockImplementation(() => {});
    const orig = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) =>
      tag === 'a' ? link : orig(tag)
    );

    return { blobParts, createObjectURL, revokeObjectURL, link, clickSpy };
  }

  it('downloads with the correct filename', () => {
    const { link, clickSpy } = setupDownloadMocks();

    downloadSimulationReportCsv('sim-dl-1', DEFAULT_SIMULATION_REPORT);

    expect(link.getAttribute('download')).toBe('sim_sim-dl-1.csv');
    expect(clickSpy).toHaveBeenCalledOnce();
  });

  it('revokes the object URL after triggering the download', () => {
    const { revokeObjectURL } = setupDownloadMocks();

    downloadSimulationReportCsv('sim-dl-2', DEFAULT_SIMULATION_REPORT);

    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test-url');
  });

  it('writes metric keys as the CSV header in SIMULATION_REPORT_METRIC_KEYS order', () => {
    const { blobParts } = setupDownloadMocks();

    downloadSimulationReportCsv('sim-dl-3', DEFAULT_SIMULATION_REPORT);

    const [header] = blobParts.join('').split('\n');
    expect(header).toBe(SIMULATION_REPORT_METRIC_KEYS.join(','));
  });

  it('writes metric values in matching column order, using empty string for null', () => {
    const { blobParts } = setupDownloadMocks();
    const report: GetSimulationReportResponse = {
      servicingToDrivingRatio: 1.5,
      vehicleUtilizationRatio: null,
      averageTasksServicedPerShift: 3,
      averageTaskResponseTime: 2.25,
      vehicleDistanceTraveled: 100,
    };

    downloadSimulationReportCsv('sim-dl-4', report);

    const [, row] = blobParts.join('').split('\n');
    expect(row).toBe('1.5,,3,2.25,100');
  });
});
