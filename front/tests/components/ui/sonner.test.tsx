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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Toaster } from '~/components/ui/sonner';
import type { ToasterProps } from 'sonner';

// Mock next-themes
vi.mock('next-themes', () => ({
  useTheme: vi.fn(),
}));

// Mock sonner
vi.mock('sonner', () => ({
  Toaster: ({
    theme,
    className,
    icons,
    style,
    expand,
    richColors,
    closeButton,
    ...props
  }: ToasterProps) => (
    <div
      data-testid="toaster"
      data-theme={theme || 'system'}
      data-classname={className}
      data-expand={expand?.toString()}
      data-richcolors={richColors?.toString()}
      data-closebutton={closeButton?.toString()}
      {...props}
    >
      {icons && (
        <>
          <div data-testid="icon-success">{icons.success}</div>
          <div data-testid="icon-info">{icons.info}</div>
          <div data-testid="icon-warning">{icons.warning}</div>
          <div data-testid="icon-error">{icons.error}</div>
          <div data-testid="icon-loading">{icons.loading}</div>
        </>
      )}
      {style && (
        <div data-testid="style-vars" data-style={JSON.stringify(style)} />
      )}
    </div>
  ),
}));

import { useTheme } from 'next-themes';

describe('Toaster Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Toaster', () => {
    it('should render toaster with default theme', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'system',
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toBeInTheDocument();
      expect(toaster).toHaveAttribute('data-theme', 'system');
    });

    it('should render toaster with light theme', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'light',
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-theme', 'light');
    });

    it('should render toaster with dark theme', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'dark',
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-theme', 'dark');
    });

    it('should default to system when theme is undefined', () => {
      vi.mocked(useTheme).mockReturnValue({
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-theme', 'system');
    });

    it('should render with correct className', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'light',
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-classname', 'toaster group');
    });

    it('should apply custom CSS variables', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'light',
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const styleVars = screen.getByTestId('style-vars');
      const style = JSON.parse(styleVars.getAttribute('data-style') || '{}');

      expect(style).toEqual({
        '--normal-bg': 'var(--popover)',
        '--normal-text': 'var(--popover-foreground)',
        '--normal-border': 'var(--border)',
        '--border-radius': 'var(--radius)',
      });
    });
  });

  describe('Icons', () => {
    beforeEach(() => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'light',
        setTheme: vi.fn(),
        themes: [],
      });
    });

    it('should render success icon', () => {
      render(<Toaster />);

      const successIcon = screen.getByTestId('icon-success');
      expect(successIcon).toBeInTheDocument();
    });

    it('should render info icon', () => {
      render(<Toaster />);

      const infoIcon = screen.getByTestId('icon-info');
      expect(infoIcon).toBeInTheDocument();
    });

    it('should render warning icon', () => {
      render(<Toaster />);

      const warningIcon = screen.getByTestId('icon-warning');
      expect(warningIcon).toBeInTheDocument();
    });

    it('should render error icon', () => {
      render(<Toaster />);

      const errorIcon = screen.getByTestId('icon-error');
      expect(errorIcon).toBeInTheDocument();
    });

    it('should render loading icon', () => {
      render(<Toaster />);

      const loadingIcon = screen.getByTestId('icon-loading');
      expect(loadingIcon).toBeInTheDocument();
    });
  });

  describe('Props forwarding', () => {
    beforeEach(() => {
      vi.mocked(useTheme).mockReturnValue({
        theme: 'light',
        setTheme: vi.fn(),
        themes: [],
      });
    });

    it('should forward position prop', () => {
      render(<Toaster position="top-right" />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('position', 'top-right');
    });

    it('should forward duration prop', () => {
      render(<Toaster duration={5000} />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('duration', '5000');
    });

    it('should forward expand prop', () => {
      render(<Toaster expand={true} />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-expand', 'true');
    });

    it('should forward visibleToasts prop', () => {
      render(<Toaster visibleToasts={3} />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('visibleToasts', '3');
    });

    it('should forward richColors prop', () => {
      render(<Toaster richColors={true} />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-richcolors', 'true');
    });

    it('should forward closeButton prop', () => {
      render(<Toaster closeButton={true} />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-closebutton', 'true');
    });
  });

  describe('Edge cases', () => {
    it('should handle null theme', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: null as unknown as string,
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-theme', 'system');
    });

    it('should handle undefined theme', () => {
      vi.mocked(useTheme).mockReturnValue({
        theme: undefined,
        setTheme: vi.fn(),
        themes: [],
      });

      render(<Toaster />);

      const toaster = screen.getByTestId('toaster');
      expect(toaster).toHaveAttribute('data-theme', 'system');
    });

    it('should not crash when useTheme returns empty object', () => {
      vi.mocked(useTheme).mockReturnValue({
        setTheme: vi.fn(),
        themes: [],
      });

      expect(() => render(<Toaster />)).not.toThrow();
    });
  });
});
