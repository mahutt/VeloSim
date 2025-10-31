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
import { render, screen, waitFor, within } from '@testing-library/react';
import api from '~/api';
import { createRoutesStub } from 'react-router';
import Users, { meta } from '~/routes/users';
import userEvent from '@testing-library/user-event';

// Mock the API module
vi.mock('~/api');
vi.mock('~/hooks/use-auth', () => ({
  default: () => ({
    user: {
      id: 1,
      username: 'Test',
      is_admin: false,
      is_enabled: true,
    },
  }),
}));

beforeEach(() => {
  vi.resetAllMocks();
});

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
});

test('users page shows list of users when data is available', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [
        {
          id: 1,
          username: 'john_doe',
          is_admin: true,
          is_enabled: true,
        },
        {
          id: 2,
          username: 'amy',
          is_admin: false,
          is_enabled: false,
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
      path: '/users',
      Component: Users,
    },
  ]);

  render(<Stub initialEntries={['/users']} />);

  expect(await screen.findByText('john_doe')).toBeInTheDocument();
  expect(await screen.findByText('amy')).toBeInTheDocument();
  expect(await screen.findAllByText('Enabled')).toHaveLength(1);
  expect(await screen.findAllByText('Disabled')).toHaveLength(1);
});

test('users page shows empty state when no users are available', async () => {
  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [],
      total: 0,
      page: 1,
      per_page: 10,
      total_pages: 0,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);

  render(<Stub initialEntries={['/users']} />);
  expect(await screen.findByText(/No results./i)).toBeInTheDocument();
});

test('ResetPasswordDialog renders when triggered', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [
        {
          id: 1,
          username: 'john_doe',
          is_admin: true,
          is_enabled: true,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);

  // Create a container for portals
  const { baseElement } = render(<Stub initialEntries={['/users']} />);

  // Find and click the menu button
  const menuButton = await screen.findByTestId('user-actions');
  await user.click(menuButton);

  // Query from baseElement instead of screen to catch portaled content
  const changePasswordButton =
    await within(baseElement).findByText('Change password');
  await user.click(changePasswordButton);

  // Check if the ResetPasswordDialog appears
  const dialogTitle = await screen.findByRole('dialog');
  expect(dialogTitle).toBeInTheDocument();
});

test('clicking enable / disable user makes API PUT request', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [
        {
          id: 1,
          username: 'john_doe',
          is_admin: true,
          is_enabled: true,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    },
  });

  vi.mocked(api.put).mockResolvedValueOnce({
    data: {
      id: 1,
      username: 'john_doe',
      is_admin: true,
      is_enabled: false,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);
  render(<Stub initialEntries={['/users']} />);
  // Find and click the menu button
  const menuButton = await screen.findByTestId('user-actions');
  await user.click(menuButton);
  const toggleEnableButton = await screen.findByText('Disable user');
  await user.click(toggleEnableButton);
  expect(api.put).toHaveBeenCalledWith('/users/1/role', {
    is_admin: true,
    is_enabled: false,
  });
});

test('clicking make / revoke admin makes API PUT request', async () => {
  const user = userEvent.setup();

  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [
        {
          id: 1,
          username: 'john_doe',
          is_admin: true,
          is_enabled: true,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    },
  });

  vi.mocked(api.put).mockResolvedValueOnce({
    data: {
      id: 1,
      username: 'john_doe',
      is_admin: false,
      is_enabled: true,
    },
  });

  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);
  render(<Stub initialEntries={['/users']} />);
  // Find and click the menu button
  const menuButton = await screen.findByTestId('user-actions');
  await user.click(menuButton);
  const toggleEnableButton = await screen.findByText('Revoke admin');
  await user.click(toggleEnableButton);
  expect(api.put).toHaveBeenCalledWith('/users/1/role', {
    is_admin: false,
    is_enabled: true,
  });
});

test('clicking make admin handles API error', async () => {
  const consoleErrorSpy = vi
    .spyOn(console, 'error')
    .mockImplementation(() => {});
  const user = userEvent.setup();

  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [
        {
          id: 1,
          username: 'john_doe',
          is_admin: false,
          is_enabled: true,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    },
  });

  const mockError = new Error('Failed to update user role');
  vi.mocked(api.put).mockRejectedValueOnce(mockError);

  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);

  render(<Stub initialEntries={['/users']} />);

  // Find and click the menu button
  const menuButton = await screen.findByTestId('user-actions');
  await user.click(menuButton);

  const revokeAdminButton = await screen.findByText('Make admin');
  await user.click(revokeAdminButton);

  // Wait for the API call to complete
  await waitFor(() => {
    expect(api.put).toHaveBeenCalledWith('/users/1/role', {
      is_admin: true,
      is_enabled: true,
    });
  });

  // Verify error was logged
  expect(consoleErrorSpy).toHaveBeenCalledWith(
    'Failed to make admin:',
    mockError
  );

  consoleErrorSpy.mockRestore();
});

test('clicking revoke admin handles API error', async () => {
  const consoleErrorSpy = vi
    .spyOn(console, 'error')
    .mockImplementation(() => {});
  const user = userEvent.setup();

  vi.mocked(api.get).mockResolvedValueOnce({
    data: {
      users: [
        {
          id: 1,
          username: 'john_doe',
          is_admin: true,
          is_enabled: true,
        },
      ],
      total: 1,
      page: 1,
      per_page: 10,
      total_pages: 1,
    },
  });

  const mockError = new Error('Failed to update user role');
  vi.mocked(api.put).mockRejectedValueOnce(mockError);

  const Stub = createRoutesStub([
    {
      path: '/users',
      Component: Users,
    },
  ]);

  render(<Stub initialEntries={['/users']} />);

  // Find and click the menu button
  const menuButton = await screen.findByTestId('user-actions');
  await user.click(menuButton);

  const revokeAdminButton = await screen.findByText('Revoke admin');
  await user.click(revokeAdminButton);

  // Wait for the API call to complete
  await waitFor(() => {
    expect(api.put).toHaveBeenCalledWith('/users/1/role', {
      is_admin: false,
      is_enabled: true,
    });
  });

  // Verify error was logged
  expect(consoleErrorSpy).toHaveBeenCalledWith(
    'Failed to revoke admin:',
    mockError
  );

  consoleErrorSpy.mockRestore();
});
