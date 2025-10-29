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

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Signin from '~/routes/login';
import axios from 'axios';
import { AuthContext } from '~/providers/auth-provider';
import { TOKEN_STORAGE_KEY } from '~/constants';

vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
    isAxiosError: () => true,
  },
}));

vi.mock('~/api', () => {
  return {
    default: {
      get: vi.fn(() =>
        Promise.resolve({
          data: {
            id: 1,
            username: 'demo_user',
            is_admin: true,
          },
        })
      ),
    },
  };
});

// Mock the login-alert component
vi.mock('~/components/login/login-alert.tsx', () => ({
  default: ({ code }: { code: number }) => (
    <div data-testid="login-alert">{code}</div>
  ),
}));

describe('Login Page', () => {
  const mockSetUser = vi.fn();
  const mockRefreshUser = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  const renderLoginPage = () => {
    return render(
      <AuthContext.Provider
        value={{
          user: null,
          setUser: mockSetUser,
          loading: false,
          setLoading: vi.fn(),
          logout: vi.fn(),
          refreshUser: mockRefreshUser,
        }}
      >
        <Signin />
      </AuthContext.Provider>
    );
  };

  it('renders login form with all fields', () => {
    renderLoginPage();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
  });

  it('shows validation errors for empty fields', async () => {
    renderLoginPage();
    const loginButton = screen.getByRole('button', { name: /log in/i });

    await userEvent.click(loginButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Username must be at least 1 character/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Password must be at least 1 character/i)
      ).toBeInTheDocument();
    });
  });

  it('handles successful login', async () => {
    renderLoginPage();
    const mockResponse = { data: { access_token: 'test-token' } };
    (axios.post as Mock).mockResolvedValueOnce(mockResponse);

    await userEvent.type(screen.getByLabelText(/username/i), 'testuser');
    await userEvent.type(screen.getByLabelText(/password/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(sessionStorage.getItem(TOKEN_STORAGE_KEY)).toBe('test-token');
      expect(mockRefreshUser).toHaveBeenCalled();
    });
  });

  it('handles login error', async () => {
    renderLoginPage();
    const mockError = {
      status: 401,
    };
    Object.defineProperty(mockError, 'isAxiosError', {
      value: () => true,
    });
    (axios.post as Mock).mockRejectedValueOnce(mockError);

    await userEvent.type(screen.getByLabelText(/username/i), 'testuser');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByTestId('login-alert')).toBeInTheDocument();
    });
  });
});
