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

import { describe, it, expect, vi, type Mock } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppSidebar } from '~/components/sidebar/app-sidebar';
import { NavUser } from '~/components/sidebar/nav-user';
import { SidebarProvider } from '~/components/ui/sidebar';
import useAuth from '~/hooks/use-auth';
import { useFeature } from '~/hooks/use-feature';

vi.mock('~/hooks/use-auth', () => ({
  default: vi.fn(),
}));
vi.mock('~/hooks/use-feature', () => ({
  useFeature: vi.fn(),
}));
vi.mock('~/components/sidebar/nav-main', () => ({
  NavMain: () => <div>nav-main</div>,
}));
vi.mock('~/components/sidebar/nav-admin', () => ({
  NavAdmin: () => <div>nav-admin</div>,
}));

describe('NavUser', () => {
  it('renders correct label for non-admin users', () => {
    (useAuth as Mock).mockReturnValue({
      user: {
        username: 'Test',
        is_admin: false,
      },
      logout: vi.fn(),
    });
    render(
      <SidebarProvider>
        <NavUser />
      </SidebarProvider>
    );
    expect(screen.getByText('User')).toBeInTheDocument();
  });
  it('renders correct label for admin users', () => {
    (useAuth as Mock).mockReturnValue({
      user: {
        username: 'Test',
        is_admin: true,
      },
      logout: vi.fn(),
    });
    render(
      <SidebarProvider>
        <NavUser />
      </SidebarProvider>
    );
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });
  it('fails to render when no user is authenticated', () => {
    (useAuth as Mock).mockReturnValue({
      user: null,
      logout: vi.fn(),
    });
    render(
      <SidebarProvider>
        <NavUser />
      </SidebarProvider>
    );
    // Elements of the role 'list' indicate that NavUser rendered something
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('AppSidebar returns nothing when sidebar feature is disabled', () => {
    (useFeature as Mock).mockReturnValue(false);
    (useAuth as Mock).mockReturnValue({ user: null, logout: vi.fn() });

    render(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>
    );

    expect(screen.queryByText('nav-main')).not.toBeInTheDocument();
    expect(screen.queryByText('nav-admin')).not.toBeInTheDocument();
  });

  it('AppSidebar hides admin section for non-admin users', () => {
    (useFeature as Mock).mockReturnValue(true);
    (useAuth as Mock).mockReturnValue({
      user: { username: 'Regular', is_admin: false },
      logout: vi.fn(),
    });

    render(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>
    );

    expect(screen.getByText('nav-main')).toBeInTheDocument();
    expect(screen.queryByText('nav-admin')).not.toBeInTheDocument();
  });

  it('AppSidebar shows admin section for admin users', () => {
    (useFeature as Mock).mockReturnValue(true);
    (useAuth as Mock).mockReturnValue({
      user: { username: 'Admin', is_admin: true },
      logout: vi.fn(),
    });

    render(
      <SidebarProvider>
        <AppSidebar />
      </SidebarProvider>
    );

    expect(screen.getByText('nav-admin')).toBeInTheDocument();
  });
});
