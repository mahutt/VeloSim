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

import { type ColumnDef } from '@tanstack/react-table';
import type { TranslationSchema } from '~/lib/i18n';
import type { Simulation } from '~/types';
import { PlaybackCell, ReportCell, ReportSummaryCell } from './report-cells';
import ReportSummaryLegendTooltip from './report-summary-legend-tooltip';

export const getColumns = (t: TranslationSchema): ColumnDef<Simulation>[] => [
  {
    accessorKey: 'id',
    header: t.simulations.column.id,
  },
  {
    accessorKey: 'name',
    header: t.simulations.column.name,
  },
  {
    accessorKey: 'date_created',
    header: t.simulations.column.created,
    cell: ({ row }) => {
      const date = new Date(row.original.date_created);
      return <span>{date.toLocaleDateString()}</span>;
    },
  },
  {
    id: 'reportSummary',
    header: () => (
      <div className="flex items-center gap-1">
        <span>{t.simulations.column.reportSummary}</span>
        <ReportSummaryLegendTooltip />
      </div>
    ),
    cell: ({ row }) => <ReportSummaryCell simId={row.original.uuid} />,
  },
  {
    id: 'report',
    header: t.simulations.column.report,
    cell: ({ row }) => (
      <ReportCell simId={row.original.uuid} simName={row.original.name} />
    ),
  },
  {
    id: 'playback',
    header: t.simulations.column.playback,
    cell: ({ row }) => {
      return (
        <PlaybackCell
          simId={row.original.uuid}
          isCompleted={row.original.completed}
        />
      );
    },
  },
];
