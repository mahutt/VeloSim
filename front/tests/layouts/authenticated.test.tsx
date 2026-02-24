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
import Authenticated from '~/layouts/authenticated';
import '@testing-library/jest-dom';
import { FeatureToggleProvider } from '~/providers/feature-toggle-provider';

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
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(typeof actual === 'object' && actual !== null ? actual : {}),
    useNavigate: () => mockNavigate,
  };
});

describe('Authenticated Layout', () => {
  const MockChild = () => (
    <div data-testid="protected-content">Protected Content</div>
  );
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  it('shows loader when authentication is loading', () => {
    (useAuth as Mock).mockReturnValue({
      loading: true,
      user: null,
    });

    const { getByTestId } = render(
      <FeatureToggleProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Authenticated />}>
              <Route path="/" element={<MockChild />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </FeatureToggleProvider>
    );

    expect(getByTestId('page-loader')).toBeInTheDocument();
  });

  it('redirects to login when user is not authenticated', async () => {
    (useAuth as Mock).mockReturnValue({
      loading: false,
      user: null,
    });

    render(
      <FeatureToggleProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Authenticated />}>
              <Route path="/" element={<MockChild />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login?next=%2F', {
        replace: true,
      });
    });
  });

  it('renders child routes when user is authenticated', () => {
    (useAuth as Mock).mockReturnValue({
      loading: false,
      user: { id: 1, username: 'Test User', is_admin: true },
    });

    const { getByTestId } = render(
      <FeatureToggleProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Authenticated />}>
              <Route path="/" element={<MockChild />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </FeatureToggleProvider>
    );

    expect(getByTestId('protected-content')).toBeInTheDocument();
  });
});
