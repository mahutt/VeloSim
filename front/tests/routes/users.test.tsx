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

import { expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createRoutesStub } from 'react-router';
import Users, { meta } from '~/routes/users';

// Mock the API module
vi.mock('~/api', () => {
  return {
    default: {
      get: vi.fn(() =>
        Promise.resolve({
          data: {
            users: [
              {
                id: 1,
                username: 'john_doe',
                is_admin: true,
              },
              {
                id: 2,
                username: 'amy',
                is_admin: false,
              },
            ],
            total: 0,
            page: 0,
            per_page: 0,
            total_pages: 0,
          },
        })
      ),
    },
  };
});

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('home pages loads 1 button', async () => {
  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);

  render(<Stub initialEntries={['/users']} />);

  expect(await screen.findByText('john_doe')).toBeInTheDocument();
  expect(await screen.findByText('amy')).toBeInTheDocument();
});
