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
import type { User } from '~/types';
import { Badge } from '../ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';
import { Button } from '../ui/button';
import api from '~/api';

export const columns: ColumnDef<User>[] = [
  {
    accessorKey: 'id',
    header: 'Id',
  },
  {
    accessorKey: 'username',
    header: 'Username',
  },
  {
    accessorKey: 'is_admin',
    header: 'Type',
    cell: ({ row }) => {
      const user = row.original;
      const label = user.is_admin ? 'Admin' : 'User';
      const variant = user.is_admin ? 'default' : 'secondary';
      return <Badge variant={variant}>{label}</Badge>;
    },
  },
  {
    accessorKey: 'is_enabled',
    header: 'Status',
    cell: ({ row }) => {
      const user = row.original;

      return (
        <span className="text-muted-foreground">
          {user.is_enabled ? 'Enabled' : 'Disabled'}
        </span>
      );
    },
  },
  {
    id: 'actions',
    enableHiding: false,
    cell: ({ row, table }) => {
      const user = row.original;
      return (
        <div className="flex justify-end gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                data-testid="user-actions"
                variant="ghost"
                className="h-8 w-8 p-0"
              >
                <span className="sr-only">Open menu</span>
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => {
                  table.options.meta?.setResetPasswordUser(user);
                  table.options.meta?.setShowResetPasswordDialog(true);
                }}
              >
                Change password
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={async () => {
                  const { data: UpdatedUser } = await api.put<User>(
                    `/users/${user.id}/role`,
                    {
                      is_admin: user.is_admin,
                      is_enabled: !user.is_enabled,
                    }
                  );
                  table.options.meta?.updateUser(UpdatedUser);
                }}
              >
                {user.is_enabled ? 'Disable user' : 'Enable user'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    },
  },
];
