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

import { fireEvent, render, screen } from '@testing-library/react';
import { vi, describe, it, expect, afterEach } from 'vitest';

const mockUseSimulation = vi.fn();
const mockUsePreferences = vi.fn();

vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: () => mockUseSimulation(),
}));
vi.mock('~/hooks/use-preferences', () => ({
  default: () => mockUsePreferences(),
}));

import ReportingWidget from '~/components/simulation/reporting-widget';
import HQWidget from '~/components/simulation/hq-widget';

describe('ReportingWidget', () => {
  afterEach(() => {
    mockUseSimulation.mockReset();
    mockUsePreferences.mockReset();
  });

  it('renders HQWidget all-quiet state and toggles open', () => {
    mockUsePreferences.mockReturnValue({
      t: {
        simulation: {
          hqWidget: {
            allQuiet: 'All quiet at HQ',
            atHQ: 'at HQ',
            noPendingShifts: 'No pending shifts',
            driverSingular: 'driver',
            driverPlural: 'drivers',
            vehicleSingular: 'vehicle',
            vehiclePlural: 'vehicles',
          },
        },
        simulations: {
          report: {
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
    });
    mockUseSimulation.mockReturnValue({
      state: {
        HQWidgetState: {
          entities: null,
          driversAtHQ: [],
          driversPendingShift: [],
        },
        reporting: {
          servicingToDrivingRatio: 1,
          vehicleUtilizationRatio: 1,
          averageTasksServicedPerShift: 1,
          averageTaskResponseTime: 1,
          vehicleDistanceTraveled: 1,
        },
      },
    });

    render(<HQWidget />);
    expect(screen.getByText('All quiet at HQ')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('No pending shifts')).toBeInTheDocument();
  });

  it('renders HQWidget driver and vehicle entity labels and driver rows', () => {
    mockUsePreferences.mockReturnValue({
      t: {
        simulation: {
          hqWidget: {
            allQuiet: 'All quiet at HQ',
            atHQ: 'at HQ',
            noPendingShifts: 'No pending shifts',
            driverSingular: 'driver',
            driverPlural: 'drivers',
            vehicleSingular: 'vehicle',
            vehiclePlural: 'vehicles',
          },
        },
        simulations: {
          report: {
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
    });

    mockUseSimulation.mockReturnValue({
      state: {
        HQWidgetState: {
          entities: { type: 'driver', count: 2 },
          driversAtHQ: [
            { id: 1, name: 'Driver A', minutesTillShift: -5 },
            { id: 2, name: 'Driver B', minutesTillShift: 10 },
          ],
          driversPendingShift: [],
        },
        reporting: {
          servicingToDrivingRatio: 1,
          vehicleUtilizationRatio: 1,
          averageTasksServicedPerShift: 1,
          averageTaskResponseTime: 1,
          vehicleDistanceTraveled: 1,
        },
      },
    });
    const { rerender } = render(<HQWidget />);
    expect(screen.getByText('2 drivers at HQ')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Driver A')).toBeInTheDocument();
    expect(screen.getByText('-0:05')).toBeInTheDocument();
    expect(screen.getByText('0:10')).toBeInTheDocument();

    mockUseSimulation.mockReturnValueOnce({
      state: {
        HQWidgetState: {
          entities: { type: 'vehicle', count: 1 },
          driversAtHQ: [],
          driversPendingShift: [],
        },
        reporting: {
          servicingToDrivingRatio: 1,
          vehicleUtilizationRatio: 1,
          averageTasksServicedPerShift: 1,
          averageTaskResponseTime: 1,
          vehicleDistanceTraveled: 1,
        },
      },
    });
    rerender(<HQWidget />);
    expect(screen.getByText('1 vehicle at HQ')).toBeInTheDocument();
  });

  it('displays a compact summary in the header', () => {
    mockUsePreferences.mockReturnValue({
      t: {
        simulations: {
          report: {
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
    });
    mockUseSimulation.mockReturnValue({
      state: {
        reporting: {
          servicingToDrivingRatio: 3.18,
          vehicleUtilizationRatio: 0.84,
          averageTasksServicedPerShift: 4,
          averageTaskResponseTime: 125,
          vehicleDistanceTraveled: 3200,
        },
      },
    });

    render(<ReportingWidget />);

    expect(screen.getByText('3.2/0.8/4.0/2m/3km')).toBeInTheDocument();
  });

  it('displays each reporting metric with formatted values', () => {
    mockUsePreferences.mockReturnValue({
      t: {
        simulations: {
          report: {
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
    });
    mockUseSimulation.mockReturnValue({
      state: {
        reporting: {
          servicingToDrivingRatio: 1.02,
          vehicleUtilizationRatio: 0.95,
          averageTasksServicedPerShift: 7.45,
          averageTaskResponseTime: 59,
          vehicleDistanceTraveled: 999,
        },
      },
    });

    render(<ReportingWidget />);

    expect(screen.getByText('Servicing to Driving Ratio')).toBeInTheDocument();
    expect(screen.getByText('1.0')).toBeInTheDocument();
    expect(screen.getByText('Vehicle Utilization Ratio')).toBeInTheDocument();
    expect(screen.getByText('0.9')).toBeInTheDocument();
    expect(
      screen.getByText('Average Tasks Serviced Per Shift')
    ).toBeInTheDocument();
    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.getByText('Average Task Response Time')).toBeInTheDocument();
    expect(screen.getByText('59s')).toBeInTheDocument();
    expect(
      screen.getByText('Total Vehicle Distance Travelled')
    ).toBeInTheDocument();
    expect(screen.getByText('999m')).toBeInTheDocument();
  });

  it('expands details while hovered and collapses when hover ends', () => {
    mockUsePreferences.mockReturnValue({
      t: {
        simulations: {
          report: {
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
    });
    mockUseSimulation.mockReturnValue({
      state: {
        reporting: {
          servicingToDrivingRatio: 1,
          vehicleUtilizationRatio: 1,
          averageTasksServicedPerShift: 1,
          averageTaskResponseTime: 1,
          vehicleDistanceTraveled: 1,
        },
      },
    });

    const { container } = render(<ReportingWidget />);

    const widget = container.firstElementChild as HTMLDivElement;
    const detailsContainer = widget.lastElementChild;
    expect(detailsContainer).toHaveClass('h-0');

    fireEvent.mouseEnter(widget);
    expect(detailsContainer).toHaveClass('h-36');

    fireEvent.mouseLeave(widget);
    expect(detailsContainer).toHaveClass('h-0');
  });
});
