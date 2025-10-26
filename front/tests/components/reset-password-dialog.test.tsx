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
import ResetPasswordDialog from '~/components/reset-password-dialog';
import { AuthContext } from '~/providers/auth-provider';
import type { User } from '~/types';
import api from '~/api';

vi.mock('~/api', () => ({
  default: {
    put: vi.fn(),
  },
}));

describe('ResetPasswordDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockUser: User = {
    id: 1,
    username: 'current_user',
    is_admin: true,
    is_enabled: true,
  };
  const mockTargetUser: User = {
    id: 2,
    username: 'target_user',
    is_admin: false,
    is_enabled: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderDialog = (
    targetUser: User = mockTargetUser,
    open: boolean = true
  ) => {
    return render(
      <AuthContext.Provider
        value={{
          user: mockUser,
          setUser: vi.fn(),
          loading: false,
          setLoading: vi.fn(),
          logout: vi.fn(),
          refreshUser: vi.fn(),
        }}
      >
        <ResetPasswordDialog
          open={open}
          onOpenChange={mockOnOpenChange}
          targetUser={targetUser}
        />
      </AuthContext.Provider>
    );
  };

  it('renders dialog with correct title for another user', () => {
    renderDialog();
    expect(
      screen.getByText(`Update password for ${mockTargetUser.username}`)
    ).toBeInTheDocument();
  });

  it('renders dialog with correct title for current user', () => {
    renderDialog(mockUser);
    expect(screen.getByText('Update your password')).toBeInTheDocument();
  });

  it('renders password form fields', () => {
    renderDialog();
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /update/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('shows validation error when passwords are empty', async () => {
    renderDialog();
    const updateButton = screen.getByRole('button', { name: /update/i });

    await userEvent.click(updateButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Password must be at least 1 character/i)
      ).toBeInTheDocument();
    });
  });

  it('shows validation error when passwords do not match', async () => {
    renderDialog();

    await userEvent.type(screen.getByLabelText(/^Password$/i), 'password123');
    await userEvent.type(
      screen.getByLabelText(/Confirm password/i),
      'password456'
    );
    await userEvent.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(screen.getByText(/Passwords don't match/i)).toBeInTheDocument();
    });
  });

  it('handles successful password update', async () => {
    renderDialog();
    (api.put as Mock).mockResolvedValueOnce({ data: mockTargetUser });

    await userEvent.type(
      screen.getByLabelText(/^Password$/i),
      'newpassword123'
    );
    await userEvent.type(
      screen.getByLabelText(/Confirm password/i),
      'newpassword123'
    );
    await userEvent.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        `/users/${mockTargetUser.id}/password`,
        {
          password: 'newpassword123',
        }
      );
      expect(
        screen.getByText(/Password updated successfully/i)
      ).toBeInTheDocument();
    });
  });

  it('handles password update error', async () => {
    renderDialog();
    (api.put as Mock).mockRejectedValueOnce(new Error('API Error'));

    await userEvent.type(
      screen.getByLabelText(/^Password$/i),
      'newpassword123'
    );
    await userEvent.type(
      screen.getByLabelText(/Confirm password/i),
      'newpassword123'
    );
    await userEvent.click(screen.getByRole('button', { name: /update/i }));

    await waitFor(() => {
      expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    });
  });

  it('calls onOpenChange when cancel button is clicked', async () => {
    renderDialog();
    const cancelButton = screen.getByRole('button', { name: /cancel/i });

    await userEvent.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalled();
  });

  it('does not render when open is false', () => {
    renderDialog(mockTargetUser, false);
    expect(screen.queryByText(/Update password/i)).not.toBeInTheDocument();
  });
});
