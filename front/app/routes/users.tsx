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

import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '~/api';
import Page from '~/components/page';
import { columns } from '~/components/users/columns';
import { DataTable } from '~/components/users/data-table';
import type { GetUsersResponse, User } from '~/types';

export function meta() {
  return [{ title: 'Users' }];
}

/*
The TanStack Table pagination guide recommends starting with client-side pagination
and moving to server-side pagination as needed: https://tanstack.com/table/latest/docs/guide/pagination

However, our getUsers API is paginated, so we make multiple calls to fetch all users.
*/
async function fetchAllUsers(): Promise<User[]> {
  const users: User[] = [];
  let page = 1;
  const perPage = 10;
  let totalPages = 1;
  while (page <= totalPages) {
    try {
      const response = await api.get<GetUsersResponse>(
        `/users?skip=${(page - 1) * perPage}&limit=${perPage}`
      );
      const data = response.data;
      users.push(...data.users);
      totalPages = data.total_pages;
      page += 1;
    } catch (error) {
      console.error('Failed to fetch users:', error);
      break;
    }
  }
  return users;
}

export default function Users() {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    fetchAllUsers().then((users) => {
      setUsers(users);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-gray-300 w-16 h-16" />
      </div>
    );
  }

  return (
    <Page>
      <div className="flex flex-col gap-2">
        <div className="text-xl">Users</div>
        <DataTable
          columns={columns}
          data={users}
          getRowId={(row) => String(row.id)}
          onAddUser={(u) => setUsers((prev) => [...prev, u])}
          onUpdateUser={(u) =>
            setUsers((prev) => prev.map((x) => (x.id === u.id ? u : x)))
          }
        />
      </div>
    </Page>
  );
}
