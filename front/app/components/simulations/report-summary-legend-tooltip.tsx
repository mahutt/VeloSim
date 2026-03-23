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

import { Info } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '~/components/ui/tooltip';
import usePreferences from '~/hooks/use-preferences';
import {
  SIMULATION_REPORT_METRIC_KEYS,
  SIMULATION_REPORT_SUMMARY_LEGEND_SELECTORS,
} from '~/utils/simulation-report';

export default function ReportSummaryLegendTooltip() {
  const { t } = usePreferences();

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="inline-flex rounded-full text-foreground/80 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          aria-label={t.simulations.report.legend.title}
        >
          <Info className="h-4 w-4" />
        </button>
      </TooltipTrigger>
      <TooltipContent
        className="max-w-xs border-0 bg-foreground p-2 text-background shadow-sm [&>svg]:bg-foreground [&>svg]:fill-foreground"
        side="top"
        align="start"
        sideOffset={8}
      >
        <div className="space-y-1 text-xs">
          <p className="font-medium">{t.simulations.report.legend.title}</p>
          {SIMULATION_REPORT_METRIC_KEYS.map((key, index) => (
            <p key={key}>
              {index + 1}.{' '}
              {SIMULATION_REPORT_SUMMARY_LEGEND_SELECTORS[index](t)}
            </p>
          ))}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
