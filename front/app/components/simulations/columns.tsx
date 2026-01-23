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

export const columns: ColumnDef<Simulation>[] = [
  {
    accessorKey: 'id',
    header: 'ID',
  },
  {
    accessorKey: 'user_id',
    header: 'User ID',
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
    accessorKey: 'date_updated',
    header: 'Updated',
    cell: ({ row }) => {
      const date = new Date(row.original.date_updated);
      return <span>{date.toLocaleDateString()}</span>;
    },
  },
  {
    id: 'resume',
    header: 'Action',
    cell: ({ row }) => {
      const sim_id = row.original.uuid;
      const isCompleted = row.original.completed;

      const navigate = useNavigate();

      const handleSimulationClick = () => {
        if (isCompleted) {
          return;
        }
        navigate(`/simulation/${sim_id}`);
      };

      if (isCompleted) {
        return <span>N/A</span>;
      }

      return (
        <Button size="sm" onClick={handleSimulationClick}>
          Resume
        </Button>
      );
    },
  },
];
