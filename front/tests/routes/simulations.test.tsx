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

import { expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import api from '~/api';
import { createRoutesStub } from 'react-router';
import Simulations, { meta } from '~/routes/simulations';
import { mockDisplayError } from 'tests/mocks';

// Mock the API module
vi.mock('~/api');

beforeEach(() => {
  vi.resetAllMocks();
});

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('simulations page shows list of simulations when data is available', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      simulations: [
        {
          id: 1001,
          user_id: 3,
          date_created: '2024-02-02T12:00:00Z',
          date_updated: '2024-02-02T12:00:00Z',
          resource_count: 99,
          station_count: 99,
          task_count: 99,
        },
        {
          id: 1002,
          user_id: 3,
          date_created: '2024-03-02T12:00:00Z',
          date_updated: '2024-03-02T12:00:00Z',
          resource_count: 99,
          station_count: 99,
          task_count: 99,
        },
      ],
      total: 2,
      page: 1,
      per_page: 10,
      total_pages: 1,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulations,
    },
  ]);

  render(<Stub initialEntries={['/simulations']} />);

  expect(await screen.findByText('1001')).toBeInTheDocument();
  expect(await screen.findByText('1002')).toBeInTheDocument();
});

test('simulations page shows empty state when no simulations are available', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      simulations: [],
      total: 0,
      page: 1,
      per_page: 10,
      total_pages: 0,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulations,
    },
  ]);

  render(<Stub initialEntries={['/simulations']} />);
  expect(await screen.findByText(/No results./i)).toBeInTheDocument();
});

test('simulations page displays error when all simulations fail to load', async () => {
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.mocked(api.get).mockRejectedValueOnce(new Error('Network Error'));
  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulations,
    },
  ]);
  render(<Stub initialEntries={['/simulations']} />);

  await waitFor(() => {
    expect(mockDisplayError).toHaveBeenCalledWith(
      'Failure loading simulations',
      'All simulations failed to load.',
      expect.any(Function)
    );
  });

  consoleSpy.mockRestore();
});

test('simulations page displays error when some simulations fail to load', async () => {
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  const fakeSimulations = Array.from({ length: 10 }, (_, i) => ({
    id: 1000 + i,
    user_id: 3,
    date_created: '2024-02-02T12:00:00Z',
    date_updated: '2024-02-02T12:00:00Z',
    resource_count: 99,
    station_count: 99,
    task_count: 99,
  }));
  vi.mocked(api.get)
    .mockResolvedValueOnce({
      data: {
        simulations: fakeSimulations,
        total: 100,
        page: 1,
        per_page: 10,
        total_pages: 10,
      },
    })
    .mockRejectedValueOnce(new Error('Network Error'));
  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulations,
    },
  ]);
  render(<Stub initialEntries={['/simulations']} />);

  await waitFor(() => {
    expect(mockDisplayError).toHaveBeenCalledWith(
      'Failure loading simulations',
      'Some simulations may be missing from the list.',
      undefined
    );
  });
  consoleSpy.mockRestore();
});
