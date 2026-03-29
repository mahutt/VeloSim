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

import { Download, Eye } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import useError from '~/hooks/use-error';
import usePreferences from '~/hooks/use-preferences';
import type { GetSimulationReportResponse } from '~/types';
import {
  DEFAULT_SIMULATION_REPORT,
  downloadSimulationReportCsv,
  getSimulationReport,
} from '~/utils/simulation-report';
import { Button } from '../ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { formatDistance, formatDuration } from '~/lib/utils';

const FALLBACK_DISPLAY = '--';
const SEPARATOR = ' / ';

export function ReportSummaryCell({ simId }: { simId: string }) {
  const { t } = usePreferences();
  const [report, setReport] = useState<GetSimulationReportResponse | null>(
    null
  );

  useEffect(() => {
    let isMounted = true;

    const fetchReport = async () => {
      try {
        const data = await getSimulationReport(simId);
        if (isMounted) {
          setReport(data);
        }
      } catch {
        if (isMounted) {
          setReport(DEFAULT_SIMULATION_REPORT);
        }
      }
    };

    fetchReport();

    return () => {
      isMounted = false;
    };
  }, [simId]);

  if (!report) {
    return (
      <span className="text-muted-foreground text-sm">{t.common.loading}</span>
    );
  }

  return (
    <span className="text-sm">
      {report.servicingToDrivingRatio?.toFixed(1) ?? FALLBACK_DISPLAY}
      {SEPARATOR}
      {report.vehicleUtilizationRatio?.toFixed(1) ?? FALLBACK_DISPLAY}
      {SEPARATOR}
      {report.averageTasksServicedPerShift?.toFixed(1) ?? FALLBACK_DISPLAY}
      {SEPARATOR}
      {report.averageTaskResponseTime !== null
        ? formatDuration(report.averageTaskResponseTime)
        : FALLBACK_DISPLAY}
      {SEPARATOR}
      {report.vehicleDistanceTraveled !== null
        ? formatDistance(report.vehicleDistanceTraveled)
        : FALLBACK_DISPLAY}
    </span>
  );
}

export function PlaybackCell({
  simId,
  isCompleted,
}: {
  simId: string;
  isCompleted: boolean;
}) {
  const { t } = usePreferences();
  const navigate = useNavigate();

  if (isCompleted) {
    return <span className="text-muted-foreground text-sm">-</span>;
  }

  return (
    <Button size="sm" onClick={() => navigate(`/simulations/${simId}`)}>
      {t.simulations.action.resume}
    </Button>
  );
}

export function ReportCell({
  simId,
  simName,
}: {
  simId: string;
  simName: string;
}) {
  const { t } = usePreferences();
  const { displayError } = useError();
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [report, setReport] = useState<GetSimulationReportResponse | null>(
    null
  );

  const handleDownloadClick = async () => {
    try {
      const data = await getSimulationReport(simId);
      downloadSimulationReportCsv(simId, data);
    } catch {
      displayError(t.simulations.error.downloadReport);
    }
  };

  const handlePreviewClick = async () => {
    setIsPreviewOpen(true);
    setLoadingPreview(true);

    try {
      const data = await getSimulationReport(simId);
      setReport(data);
    } catch {
      displayError(t.simulations.error.previewReport);
      setReport(DEFAULT_SIMULATION_REPORT);
    } finally {
      setLoadingPreview(false);
    }
  };

  return (
    <>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={handleDownloadClick}>
          <Download className="h-4 w-4" /> {t.simulations.action.download}
        </Button>
        <Button size="sm" variant="outline" onClick={handlePreviewClick}>
          <Eye className="h-4 w-4" /> {t.simulations.action.preview}
        </Button>
      </div>

      <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{simName}</DialogTitle>
            <DialogDescription>
              {t.simulations.report.overview}
            </DialogDescription>
          </DialogHeader>

          {loadingPreview && (
            <div className="text-muted-foreground text-sm">
              {t.simulations.report.loading}
            </div>
          )}

          {!loadingPreview && report && (
            <div className="space-y-3 text-sm">
              <div>
                {t.simulations.report.legend.servicingToDrivingRatio}:{' '}
                {report.servicingToDrivingRatio?.toFixed(2) ?? FALLBACK_DISPLAY}
              </div>
              <div>
                {t.simulations.report.legend.vehicleUtilizationRatio}:{' '}
                {report.vehicleUtilizationRatio?.toFixed(2) ?? FALLBACK_DISPLAY}
              </div>
              <div>
                {t.simulations.report.legend.averageTasksServicedPerShift}:{' '}
                {report.averageTasksServicedPerShift?.toFixed(2) ??
                  FALLBACK_DISPLAY}
              </div>
              <div>
                {t.simulations.report.legend.averageTaskResponseTime}:{' '}
                {report.averageTaskResponseTime !== null
                  ? formatDuration(report.averageTaskResponseTime)
                  : FALLBACK_DISPLAY}
              </div>
              <div>
                {t.simulations.report.legend.totalVehicleDistanceTravelled}:{' '}
                {report.vehicleDistanceTraveled !== null
                  ? formatDistance(report.vehicleDistanceTraveled)
                  : FALLBACK_DISPLAY}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
