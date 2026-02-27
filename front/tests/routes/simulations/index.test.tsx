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
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import api from '~/api';
import { createRoutesStub } from 'react-router';
import Simulations, { meta } from '~/routes/simulations/index';
import { mockDisplayError } from 'tests/mocks';
import { makeSimulation } from 'tests/test-helpers';

// Mock the API module
vi.mock('~/api');

vi.mock('~/hooks/use-feature', () => ({
  useFeature: vi.fn(),
}));

vi.mock('~/hooks/use-error', () => ({
  default: vi.fn(),
}));

const { mockNavigate } = await vi.hoisted(async () => {
  const mockNavigate = vi.fn();
  return {
    mockNavigate,
  };
});
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

beforeEach(async () => {
  vi.resetAllMocks();

  const { useFeature } = await import('~/hooks/use-feature');
  const useError = await import('~/hooks/use-error');

  vi.mocked(useFeature).mockReturnValue(true);
  vi.mocked(useError.default).mockReturnValue({
    displayError: mockDisplayError,
  });
});

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('simulations page shows list of simulations when data is available', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      simulations: [
        makeSimulation({ id: 1001, name: 'Test Simulation 1' }),
        makeSimulation({ id: 1002, name: 'Test Simulation 2' }),
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
  const fakeSimulations = Array.from({ length: 10 }, (_, i) =>
    makeSimulation({ id: 1000 + i })
  );
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

test('simulations page navigates to simulation page on resume', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      simulations: [
        makeSimulation({
          id: 1001,
          uuid: 'sim-uuid-1001',
          name: 'Test Simulation 1',
          completed: false,
        }),
      ],
      total: 1,
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

  await waitFor(() => {
    expect(screen.getByText('Test Simulation 1')).toBeInTheDocument();
  });

  const resumeButton = screen.getByRole('button', {
    name: /resume/i,
  });
  fireEvent.click(resumeButton);
  expect(mockNavigate).toHaveBeenCalledWith('/simulations/sim-uuid-1001');
});

test('simulations page downloads a simulation report as csv', async () => {
  vi.mocked(api.get)
    .mockResolvedValueOnce({
      data: {
        simulations: [
          makeSimulation({
            id: 1001,
            uuid: 'sim-uuid-1001',
            name: 'Test Simulation 1',
            completed: false,
          }),
        ],
        total: 1,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    })
    .mockResolvedValueOnce({
      data: {
        servicingToDrivingRatio: 1.5,
        vehicleUtilizationRatio: 0.8,
      },
    });

  const createObjectURL = vi.fn(() => 'blob:report-url');
  const revokeObjectURL = vi.fn();
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    writable: true,
    value: createObjectURL,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    writable: true,
    value: revokeObjectURL,
  });

  const createdLink = document.createElement('a');
  const clickSpy = vi.spyOn(createdLink, 'click').mockImplementation(() => {});
  const originalCreateElement = document.createElement.bind(document);
  const createElementSpy = vi
    .spyOn(document, 'createElement')
    .mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return createdLink;
      }
      return originalCreateElement(tagName);
    });

  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulations,
    },
  ]);

  render(<Stub initialEntries={['/simulations']} />);

  await waitFor(() => {
    expect(screen.getByText('Test Simulation 1')).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole('button', { name: /report/i }));

  await waitFor(() => {
    expect(api.get).toHaveBeenLastCalledWith(
      '/simulation/sim-uuid-1001/report'
    );
  });

  expect(createObjectURL).toHaveBeenCalledOnce();
  expect(createdLink.getAttribute('download')).toBe('sim_sim-uuid-1001.csv');
  expect(createdLink.href).toBe('blob:report-url');
  expect(clickSpy).toHaveBeenCalledOnce();
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:report-url');

  createElementSpy.mockRestore();
  clickSpy.mockRestore();
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    writable: true,
    value: originalCreateObjectURL,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    writable: true,
    value: originalRevokeObjectURL,
  });
});

test('simulations page displays an error when report download fails', async () => {
  vi.mocked(api.get)
    .mockResolvedValueOnce({
      data: {
        simulations: [
          makeSimulation({
            id: 1001,
            uuid: 'sim-uuid-1001',
            name: 'Test Simulation 1',
            completed: false,
          }),
        ],
        total: 1,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    })
    .mockRejectedValueOnce(new Error('Report download failed'));

  const Stub = createRoutesStub([
    {
      path: '/simulations',
      Component: Simulations,
    },
  ]);

  render(<Stub initialEntries={['/simulations']} />);

  await waitFor(() => {
    expect(screen.getByText('Test Simulation 1')).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole('button', { name: /report/i }));

  await waitFor(() => {
    expect(mockDisplayError).toHaveBeenCalledWith(
      'Error downloading simulation report'
    );
  });
});
