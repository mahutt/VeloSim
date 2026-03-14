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
import { useNavigate } from 'react-router';
import type { Simulation } from '~/types';
import { Button } from '../ui/button';
import { Download } from 'lucide-react';
import api from '~/api';
import useError from '~/hooks/use-error';
import type { GetSimulationReportResponse } from '~/types';

export const columns: ColumnDef<Simulation>[] = [
  {
    accessorKey: 'id',
    header: 'ID',
  },
  {
    accessorKey: 'name',
    header: 'Name',
  },
  {
    accessorKey: 'date_created',
    header: 'Created',
    cell: ({ row }) => {
      const date = new Date(row.original.date_created);
      return <span>{date.toLocaleDateString()}</span>;
    },
  },
  {
    id: 'resumeOrReport',
    header: 'Action',
    cell: ({ row }) => {
      const sim_id = row.original.uuid;
      const isCompleted = row.original.completed;

      const navigate = useNavigate();
      const { displayError } = useError();

      const handleSimulationClick = () => {
        if (isCompleted) {
          return;
        }
        navigate(`/simulations/${sim_id}`);
      };

      const handleReportClick = async () => {
        try {
          const response = await api.get<GetSimulationReportResponse>(
            `/simulation/${sim_id}/report`
          );

          const header = Object.keys(response.data).join(',');
          const rows = Object.values(response.data).join(',');

          const csvDataString = [header, rows].join('\n');
          const blob = new Blob([csvDataString], {
            type: 'text/csv;charset=utf-8;',
          });
          const url = URL.createObjectURL(blob);

          const link = document.createElement('a');
          link.href = url;
          link.setAttribute('download', `sim_${sim_id}.csv`);
          document.body.appendChild(link);
          link.click();

          document.body.removeChild(link);
          URL.revokeObjectURL(url);
        } catch {
          displayError('Error downloading simulation report');
        }
      };

      return (
        <div className="flex gap-2">
          {!isCompleted && (
            <Button size="sm" onClick={handleSimulationClick}>
              Resume
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={handleReportClick}>
            <Download /> Report
          </Button>
        </div>
      );
    },
  },
];
