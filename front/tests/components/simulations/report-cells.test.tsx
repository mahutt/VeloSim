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

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

const {
  mockNavigate,
  mockDisplayError,
  mockGetSimulationReport,
  mockDownloadSimulationReportCsv,
} = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockDisplayError: vi.fn(),
  mockGetSimulationReport: vi.fn(),
  mockDownloadSimulationReportCsv: vi.fn(),
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('~/hooks/use-error', () => ({
  default: () => ({
    displayError: mockDisplayError,
  }),
}));

vi.mock('~/hooks/use-preferences', () => ({
  default: () => ({
    t: {
      common: {
        loading: 'Loading...',
      },
      simulations: {
        action: {
          resume: 'Resume',
          download: 'Download',
          preview: 'Preview',
        },
        error: {
          downloadReport: 'Download failed',
          previewReport: 'Preview failed',
        },
        report: {
          overview: 'Simulation report overview',
          loading: 'Loading report...',
          legend: {
            servicingToDrivingRatio: 'Servicing to Driving Ratio',
            vehicleUtilizationRatio: 'Vehicle Utilization Ratio',
            averageTasksServicedPerShift: 'Average Tasks Serviced Per Shift',
            averageTaskResponseTime: 'Average Task Response Time',
            totalVehicleDistanceTravelled: 'Total Vehicle Distance Travelled',
          },
        },
      },
    },
  }),
}));

vi.mock('~/utils/simulation-report', () => ({
  DEFAULT_SIMULATION_REPORT: {
    servicingToDrivingRatio: null,
    vehicleUtilizationRatio: null,
    averageTasksServicedPerShift: null,
    averageTaskResponseTime: null,
    vehicleDistanceTraveled: null,
  },
  getSimulationReport: mockGetSimulationReport,
  downloadSimulationReportCsv: mockDownloadSimulationReportCsv,
}));

import {
  PlaybackCell,
  ReportCell,
  ReportSummaryCell,
} from '~/components/simulations/report-cells';

describe('report-cells', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading then formatted summary metrics in ReportSummaryCell', async () => {
    let resolveReport: (value: unknown) => void;
    const reportPromise = new Promise((resolve) => {
      resolveReport = resolve;
    });
    mockGetSimulationReport.mockReturnValue(reportPromise);

    render(<ReportSummaryCell simId="sim-1" />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    resolveReport!({
      servicingToDrivingRatio: 3.18,
      vehicleUtilizationRatio: 0.84,
      averageTasksServicedPerShift: 4,
      averageTaskResponseTime: 125,
      vehicleDistanceTraveled: 3200,
    });

    expect(
      await screen.findByText('3.2 / 0.8 / 4.0 / 2m / 3km')
    ).toBeInTheDocument();
  });

  it('renders fallback summary values when report fetch fails', async () => {
    mockGetSimulationReport.mockRejectedValueOnce(new Error('network error'));

    render(<ReportSummaryCell simId="sim-2" />);

    expect(
      await screen.findByText('-- / -- / -- / -- / --')
    ).toBeInTheDocument();
  });

  it('renders dash in PlaybackCell when simulation is completed', () => {
    render(<PlaybackCell simId="sim-3" isCompleted={true} />);

    expect(screen.getByText('-')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Resume' })
    ).not.toBeInTheDocument();
  });

  it('navigates to simulation page on PlaybackCell resume click', () => {
    render(<PlaybackCell simId="sim-4" isCompleted={false} />);

    fireEvent.click(screen.getByRole('button', { name: 'Resume' }));
    expect(mockNavigate).toHaveBeenCalledWith('/simulations/sim-4');
  });

  it('downloads report csv when download action succeeds', async () => {
    mockGetSimulationReport.mockResolvedValueOnce({
      servicingToDrivingRatio: 1.2,
      vehicleUtilizationRatio: 0.7,
      averageTasksServicedPerShift: 3.4,
      averageTaskResponseTime: 90,
      vehicleDistanceTraveled: 1500,
    });

    render(<ReportCell simId="sim-5" simName="Simulation 5" />);

    fireEvent.click(screen.getByRole('button', { name: /download/i }));

    await waitFor(() => {
      expect(mockGetSimulationReport).toHaveBeenCalledWith('sim-5');
      expect(mockDownloadSimulationReportCsv).toHaveBeenCalledWith('sim-5', {
        servicingToDrivingRatio: 1.2,
        vehicleUtilizationRatio: 0.7,
        averageTasksServicedPerShift: 3.4,
        averageTaskResponseTime: 90,
        vehicleDistanceTraveled: 1500,
      });
    });
  });

  it('shows download error when report download fetch fails', async () => {
    mockGetSimulationReport.mockRejectedValueOnce(new Error('download failed'));

    render(<ReportCell simId="sim-6" simName="Simulation 6" />);

    fireEvent.click(screen.getByRole('button', { name: /download/i }));

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith('Download failed');
    });
  });

  it('opens preview and renders report metrics when fetch succeeds', async () => {
    mockGetSimulationReport.mockResolvedValueOnce({
      servicingToDrivingRatio: 1.23,
      vehicleUtilizationRatio: 0.99,
      averageTasksServicedPerShift: 4.56,
      averageTaskResponseTime: 59,
      vehicleDistanceTraveled: 999,
    });

    render(<ReportCell simId="sim-7" simName="Simulation 7" />);

    fireEvent.click(screen.getByRole('button', { name: /preview/i }));

    expect(await screen.findByText('Simulation 7')).toBeInTheDocument();
    expect(screen.getByText('Simulation report overview')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText('Loading report...')).not.toBeInTheDocument();
    });

    expect(screen.getByText(/Servicing to Driving Ratio:/)).toBeInTheDocument();
    expect(screen.getByText(/1.23/)).toBeInTheDocument();
    expect(screen.getByText(/Vehicle Utilization Ratio:/)).toBeInTheDocument();
    expect(screen.getByText(/0.99/)).toBeInTheDocument();
    expect(
      screen.getByText(/Average Tasks Serviced Per Shift:/)
    ).toBeInTheDocument();
    expect(screen.getByText(/4.56/)).toBeInTheDocument();
    expect(screen.getByText(/Average Task Response Time:/)).toBeInTheDocument();
    expect(screen.getByText(/59s/)).toBeInTheDocument();
    expect(
      screen.getByText(/Total Vehicle Distance Travelled:/)
    ).toBeInTheDocument();
    expect(screen.getByText(/999m/)).toBeInTheDocument();
  });

  it('shows preview error and fallback values when preview fetch fails', async () => {
    mockGetSimulationReport.mockRejectedValueOnce(new Error('preview failed'));

    render(<ReportCell simId="sim-8" simName="Simulation 8" />);

    fireEvent.click(screen.getByRole('button', { name: /preview/i }));

    expect(await screen.findByText('Simulation 8')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith('Preview failed');
      expect(screen.queryByText('Loading report...')).not.toBeInTheDocument();
    });

    expect(screen.getAllByText(/--/)).not.toHaveLength(0);
  });
});
