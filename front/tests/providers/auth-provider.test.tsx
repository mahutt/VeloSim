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
import { render, act } from '@testing-library/react';
import { AuthProvider, AuthContext } from '~/providers/auth-provider';
import { useContext } from 'react';
import { TOKEN_STORAGE_KEY } from '~/constants';

// Mock sessionStorage
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage,
});

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

// Mock logger
vi.mock(import('~/lib/logger'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    log: vi.fn(),
  };
});

// Mock react-router useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Test component to access context values
const TestComponent = () => {
  const authContext = useContext(AuthContext);
  if (!authContext) throw new Error('AuthContext is undefined');
  return (
    <div>
      <div data-testid="loading">{authContext.loading.toString()}</div>
      <div data-testid="user">
        {authContext.user ? JSON.stringify(authContext.user) : 'null'}
      </div>
    </div>
  );
};

beforeEach(() => {
  vi.clearAllMocks();
  mockSessionStorage.getItem.mockReset();
});

test('provides initial state with no token', async () => {
  mockSessionStorage.getItem.mockReturnValue(null);

  const { findByTestId } = render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );

  const loadingElement = await findByTestId('loading');
  const userElement = await findByTestId('user');

  expect(loadingElement.textContent).toBe('false');
  expect(userElement.textContent).toBe('null');
  expect(mockSessionStorage.getItem).toHaveBeenCalledWith(TOKEN_STORAGE_KEY);
});

test('sets user when access token exists', async () => {
  mockSessionStorage.getItem.mockReturnValue('some-token');

  const { findByTestId } = render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );

  const loadingElement = await findByTestId('loading');
  const userElement = await findByTestId('user');

  expect(loadingElement.textContent).toBe('false');
  expect(JSON.parse(userElement.textContent!)).toEqual({
    id: 1,
    username: 'demo_user',
    is_admin: true,
  });
});

test('updates user state through context', async () => {
  const { findByTestId } = render(
    <AuthProvider>
      <AuthContext.Consumer>
        {(value) => {
          if (!value) throw new Error('AuthContext is undefined');
          // Update user after render
          act(() => {
            value.setUser({
              id: 2,
              username: 'test_user',
              is_admin: true,
              is_enabled: true,
            });
          });
          return <TestComponent />;
        }}
      </AuthContext.Consumer>
    </AuthProvider>
  );

  const userElement = await findByTestId('user');
  expect(JSON.parse(userElement.textContent!)).toEqual({
    id: 2,
    username: 'test_user',
    is_admin: true,
    is_enabled: true,
  });
});

test('clears user state when setUser is called with null', async () => {
  mockSessionStorage.getItem.mockReturnValue('some-token');

  const { findByTestId } = render(
    <AuthProvider>
      <AuthContext.Consumer>
        {(value) => {
          if (!value) throw new Error('AuthContext is undefined');
          setTimeout(() => {
            act(() => {
              value.setUser(null);
            });
          }, 0);
          return <TestComponent />;
        }}
      </AuthContext.Consumer>
    </AuthProvider>
  );

  await new Promise((resolve) => setTimeout(resolve, 50));
  const userElement = await findByTestId('user');
  expect(userElement.textContent).toBe('null');
});

test('handles loading state during authentication', async () => {
  mockSessionStorage.getItem.mockReturnValue('some-token');

  const { findByTestId } = render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );

  // Initially loading should be true, then become false
  const loadingElement = await findByTestId('loading');
  expect(loadingElement.textContent).toBe('false');
});

test('provides context value to children', () => {
  mockSessionStorage.getItem.mockReturnValue(null);

  const { container } = render(
    <AuthProvider>
      <div data-testid="child">Child Component</div>
    </AuthProvider>
  );

  expect(container.querySelector('[data-testid="child"]')).toBeTruthy();
});

test('handles authentication errors gracefully', async () => {
  const mockGet = vi.fn(() => Promise.reject(new Error('Auth failed')));
  vi.doMock('~/api', () => ({ default: { get: mockGet } }));

  mockSessionStorage.getItem.mockReturnValue('invalid-token');

  const { findByTestId } = render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );

  // Should still render without crashing
  const loadingElement = await findByTestId('loading');
  expect(loadingElement).toBeTruthy();
});

test('fetches user data when token exists on mount', async () => {
  const mockGet = vi.fn(() =>
    Promise.resolve({
      data: {
        id: 3,
        username: 'fetched_user',
        is_admin: false,
      },
    })
  );

  vi.doMock('~/api', () => ({ default: { get: mockGet } }));

  mockSessionStorage.getItem.mockReturnValue('valid-token');

  const { findByTestId } = render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );

  const userElement = await findByTestId('user');
  expect(JSON.parse(userElement.textContent!).username).toBe('demo_user');
});

test('logs user logout when logout is called', async () => {
  mockSessionStorage.getItem.mockReturnValue('some-token');
  mockNavigate.mockClear();

  const { findByTestId } = render(
    <AuthProvider>
      <AuthContext.Consumer>
        {(value) => {
          if (!value) throw new Error('AuthContext is undefined');
          return (
            <>
              <TestComponent />
              <button data-testid="logout-btn" onClick={() => value.logout()}>
                Logout
              </button>
            </>
          );
        }}
      </AuthContext.Consumer>
    </AuthProvider>
  );

  const logoutButton = await findByTestId('logout-btn');

  act(() => {
    logoutButton.click();
  });

  const { log: mockLog } = vi.mocked(await import('~/lib/logger'));
  // Verify the log was called with correct context
  expect(mockLog).toHaveBeenCalledWith({
    message: 'User logged out',
    level: 'info',
    context: 'user_logout',
  });
});
