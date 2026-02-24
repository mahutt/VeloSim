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

import { describe, it, vi, expect, beforeEach, type Mock } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { BrowserRouter, Route, Routes } from 'react-router';
import Unauthenticated from '~/layouts/unauthenticated';
import '@testing-library/jest-dom';

// Mock the useAuth hook
vi.mock('~/hooks/use-auth', () => ({
  default: vi.fn(),
}));

// Mock the page loader component
vi.mock('~/components/page-loader', () => ({
  default: () => <div data-testid="page-loader">Loading...</div>,
}));

// Import the mocked useAuth to control its return values
import useAuth from '~/hooks/use-auth';

// Mock useNavigate hook
const mockNavigate = vi.fn();
const mockUseLocation = vi.fn(() => ({
  pathname: '/login',
  search: '',
  hash: '',
  state: null,
  key: 'default',
}));
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(typeof actual === 'object' && actual !== null ? actual : {}),
    useNavigate: () => mockNavigate,
    useLocation: () => mockUseLocation(),
  };
});

describe('Unauthenticated Layout', () => {
  const MockChild = () => (
    <div data-testid="no-auth-content">No Auth Content</div>
  );
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    mockUseLocation.mockReturnValue({
      pathname: '/login',
      search: '',
      hash: '',
      state: null,
      key: 'default',
    });
  });

  it('shows loader when authentication is loading', () => {
    (useAuth as Mock).mockReturnValue({
      loading: true,
      user: null,
    });

    const { getByTestId } = render(
      <BrowserRouter>
        <Routes>
          <Route element={<Unauthenticated />}>
            <Route path="/" element={<MockChild />} />
          </Route>
        </Routes>
      </BrowserRouter>
    );

    expect(getByTestId('page-loader')).toBeInTheDocument();
  });

  it('redirects to / when user is authenticated and next is absent', async () => {
    (useAuth as Mock).mockReturnValue({
      loading: false,
      user: { id: 'user1', name: 'Test User' },
    });

    render(
      <BrowserRouter>
        <Routes>
          <Route element={<Unauthenticated />}>
            <Route path="/" element={<MockChild />} />
          </Route>
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('redirects to safe next path when user is authenticated', async () => {
    (useAuth as Mock).mockReturnValue({
      loading: false,
      user: { id: 'user1', name: 'Test User' },
    });
    mockUseLocation.mockReturnValue({
      pathname: '/login',
      search: '?next=%2Fsimulation%2Fabc-123',
      hash: '',
      state: null,
      key: 'default',
    });

    render(
      <BrowserRouter>
        <Routes>
          <Route element={<Unauthenticated />}>
            <Route path="/" element={<MockChild />} />
          </Route>
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/simulation/abc-123', {
        replace: true,
      });
    });
  });

  it('ignores unsafe next path when user is authenticated', async () => {
    (useAuth as Mock).mockReturnValue({
      loading: false,
      user: { id: 'user1', name: 'Test User' },
    });
    mockUseLocation.mockReturnValue({
      pathname: '/login',
      search: '?next=%2F%2Fevil.example%2Fphish',
      hash: '',
      state: null,
      key: 'default',
    });

    render(
      <BrowserRouter>
        <Routes>
          <Route element={<Unauthenticated />}>
            <Route path="/" element={<MockChild />} />
          </Route>
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('renders child routes when user is unauthenticated', () => {
    (useAuth as Mock).mockReturnValue({
      loading: false,
      user: null,
    });

    const { getByTestId } = render(
      <BrowserRouter>
        <Routes>
          <Route element={<Unauthenticated />}>
            <Route path="/" element={<MockChild />} />
          </Route>
        </Routes>
      </BrowserRouter>
    );

    expect(getByTestId('no-auth-content')).toBeInTheDocument();
  });
});
