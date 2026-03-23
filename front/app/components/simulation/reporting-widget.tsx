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

import { ChevronLeft, Gauge } from 'lucide-react';
import { useState } from 'react';
import usePreferences from '~/hooks/use-preferences';
import { formatDistance, formatDuration } from '~/lib/utils';
import { useSimulation } from '~/providers/simulation-provider';
import type { SimulationReport } from '~/types';

function summarize(report: SimulationReport): string {
  const summary = [
    report.servicingToDrivingRatio.toFixed(1),
    report.vehicleUtilizationRatio.toFixed(1),
    report.averageTasksServicedPerShift.toFixed(1),
    formatDuration(report.averageTaskResponseTime),
    formatDistance(report.vehicleDistanceTraveled),
  ].join('/');

  return summary;
}

export default function ReportingWidget() {
  const { t } = usePreferences();
  const { state } = useSimulation();
  const { reporting } = state;
  const [open, setOpen] = useState(false);
  return (
    <div className="w-full bg-gray-50 border shadow rounded-lg">
      {/* header */}
      <button
        className={
          'w-full flex flex-row items-center gap-2 hover:bg-gray-100 p-2 rounded-lg'
        }
        onClick={() => setOpen((prev) => !prev)}
      >
        <Gauge size={20} />
        <p className="flex-1 text-left text-muted-foreground">
          {summarize(reporting)}
        </p>
        <ChevronLeft
          size={20}
          className={`transition-transform duration-200 ${open ? '-rotate-90' : 'rotate-0'}`}
        />
      </button>
      {/* body */}
      <div className={`${open ? 'h-32' : 'h-0'} duration-200 overflow-hidden`}>
        <div className="overflow-y-auto h-32">
          <ReportingMetricRow
            label={t.simulations.report.legend.servicingToDrivingRatio}
            value={reporting.servicingToDrivingRatio.toFixed(1)}
          />
          <ReportingMetricRow
            label={t.simulations.report.legend.vehicleUtilizationRatio}
            value={reporting.vehicleUtilizationRatio.toFixed(1)}
          />
          <ReportingMetricRow
            label={t.simulations.report.legend.averageTasksServicedPerShift}
            value={reporting.averageTasksServicedPerShift.toFixed(1)}
          />
          <ReportingMetricRow
            label={t.simulations.report.legend.averageTaskResponseTime}
            value={formatDuration(reporting.averageTaskResponseTime)}
          />
          <ReportingMetricRow
            label={t.simulations.report.legend.totalVehicleDistanceTravelled}
            value={formatDistance(reporting.vehicleDistanceTraveled)}
          />
        </div>
      </div>
    </div>
  );
}

function ReportingMetricRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex flex-row items-center gap-1 px-3 py-1 text-sm font-mono">
      <span>{label}</span>
      <span className="ml-auto">{value}</span>
    </div>
  );
}
