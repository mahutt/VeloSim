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
import NewUserDialog from '~/components/users/new-user-dialog';
import type { User } from '~/types';
import api from '~/api';
import axios from 'axios';

vi.mock('~/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

vi.mock('axios', () => ({
  default: {
    isAxiosError: vi.fn(),
  },
}));

describe('NewUserDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnAddUser = vi.fn();
  const mockNewUser: User = {
    id: 3,
    username: 'new_user',
    is_admin: false,
    is_enabled: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderDialog = (open: boolean = true) => {
    return render(
      <NewUserDialog
        open={open}
        onOpenChange={mockOnOpenChange}
        onAddUser={mockOnAddUser}
      />
    );
  };

  it('renders dialog with correct title', () => {
    renderDialog();
    expect(screen.getByText('Create new user')).toBeInTheDocument();
  });

  it('shows validation error when username is empty', async () => {
    renderDialog();
    const createButton = screen.getByRole('button', { name: /create/i });

    await userEvent.click(createButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Username must be at least 1 character/i)
      ).toBeInTheDocument();
    });
  });

  it('shows validation error when password is empty', async () => {
    renderDialog();

    await userEvent.type(screen.getByLabelText(/^Username$/i), 'testuser');
    await userEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Password must be at least 1 character/i)
      ).toBeInTheDocument();
    });
  });

  it('handles successful user creation', async () => {
    renderDialog();
    (api.post as Mock).mockResolvedValueOnce({ data: mockNewUser });

    await userEvent.type(screen.getByLabelText(/^Username$/i), 'new_user');
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/users/create', {
        username: 'new_user',
        password: 'password123',
        is_admin: false,
        is_enabled: true,
      });
      expect(mockOnAddUser).toHaveBeenCalledWith(mockNewUser);
      expect(
        screen.getByText(/User created successfully/i)
      ).toBeInTheDocument();
    });
  });

  it('handles user creation with admin and enabled checkboxes', async () => {
    renderDialog();
    (api.post as Mock).mockResolvedValueOnce({
      data: { ...mockNewUser, is_admin: true, is_enabled: false },
    });

    await userEvent.type(screen.getByLabelText(/^Username$/i), 'admin_user');
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'adminpass');
    await userEvent.click(screen.getByLabelText(/^Admin$/i));
    await userEvent.click(screen.getByLabelText(/^Enabled$/i));
    await userEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/users/create', {
        username: 'admin_user',
        password: 'adminpass',
        is_admin: true,
        is_enabled: false,
      });
    });
  });

  it('handles user creation error with API detail message', async () => {
    renderDialog();
    const errorDetail = 'Username already exists';
    (axios.isAxiosError as unknown as Mock).mockReturnValueOnce(true);
    (api.post as Mock).mockRejectedValueOnce({
      response: {
        data: {
          detail: errorDetail,
        },
      },
    });

    await userEvent.type(screen.getByLabelText(/^Username$/i), 'existing_user');
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(errorDetail)).toBeInTheDocument();
    });
  });

  it('handles user creation error with generic message', async () => {
    renderDialog();
    (axios.isAxiosError as unknown as Mock).mockReturnValueOnce(false);
    (api.post as Mock).mockRejectedValueOnce(new Error('Network Error'));

    await userEvent.type(screen.getByLabelText(/^Username$/i), 'new_user');
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'password123');
    await userEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    });
  });

  it('does not render when open is false', () => {
    renderDialog(false);
    expect(screen.queryByText(/Create new user/i)).not.toBeInTheDocument();
  });

  it('resets form when dialog is closed and reopened', async () => {
    const { rerender } = renderDialog(true);

    await userEvent.type(screen.getByLabelText(/^Username$/i), 'testuser');
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'testpass');

    rerender(
      <NewUserDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        onAddUser={mockOnAddUser}
      />
    );

    rerender(
      <NewUserDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onAddUser={mockOnAddUser}
      />
    );

    expect(screen.getByLabelText(/^Username$/i)).toHaveValue('');
    expect(screen.getByLabelText(/^Password$/i)).toHaveValue('');
  });
});
