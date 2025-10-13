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

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Separator } from '~/components/ui/separator';

describe('Separator Component', () => {
  it('should render separator with default classes', () => {
    render(<Separator data-testid="separator" />);

    const separator = screen.getByTestId('separator');
    expect(separator).toBeInTheDocument();
    expect(separator.getAttribute('data-orientation')).toBe('horizontal');
    expect(separator).toHaveAttribute('role', 'none'); // Radix UI sets role to 'none' when decorative=true
    expect(separator.className).toContain('shrink-0');
    expect(separator.className).toContain('bg-border');
    expect(separator.className).toContain('data-[orientation=horizontal]:h-px');
    expect(separator.className).toContain(
      'data-[orientation=horizontal]:w-full'
    );
  });

  it('should render separator with horizontal orientation explicitly', () => {
    render(<Separator orientation="horizontal" data-testid="separator" />);

    const separator = screen.getByTestId('separator');
    expect(separator.getAttribute('data-orientation')).toBe('horizontal');
    expect(separator.className).toContain('data-[orientation=horizontal]:h-px');
    expect(separator.className).toContain(
      'data-[orientation=horizontal]:w-full'
    );
  });

  it('should render separator with vertical orientation', () => {
    render(<Separator orientation="vertical" data-testid="separator" />);

    const separator = screen.getByTestId('separator');
    expect(separator.getAttribute('data-orientation')).toBe('vertical');
    expect(separator.className).toContain('data-[orientation=vertical]:h-full');
    expect(separator.className).toContain('data-[orientation=vertical]:w-px');
  });

  it('should render separator with decorative=true', () => {
    render(<Separator decorative data-testid="separator" />);

    const separator = screen.getByTestId('separator');
    expect(separator).toHaveAttribute('role', 'none'); // Radix UI sets 'none' for decorative separators
    expect(separator).toHaveAttribute('data-slot', 'separator');
  });

  it('should render separator with decorative=false', () => {
    render(<Separator decorative={false} data-testid="separator" />);

    const separator = screen.getByTestId('separator');
    expect(separator).toHaveAttribute('role', 'separator');
    expect(separator).not.toHaveAttribute('aria-hidden');
  });

  it('should render separator with custom className', () => {
    render(<Separator className="custom-separator" data-testid="separator" />);

    const separator = screen.getByTestId('separator');
    expect(separator.className).toContain('custom-separator');
    expect(separator.className).toContain('shrink-0');
    expect(separator.className).toContain('bg-border');
  });

  it('should merge custom className with default classes', () => {
    render(
      <Separator
        className="my-4 border-red-500"
        orientation="vertical"
        data-testid="separator"
      />
    );

    const separator = screen.getByTestId('separator');
    expect(separator.className).toContain('my-4');
    expect(separator.className).toContain('border-red-500');
    expect(separator.className).toContain('shrink-0');
    expect(separator.className).toContain('bg-border');
    expect(separator.className).toContain('data-[orientation=vertical]:h-full');
    expect(separator.className).toContain('data-[orientation=vertical]:w-px');
  });

  it('should pass through other props to the underlying element', () => {
    render(
      <Separator
        data-testid="separator"
        aria-label="Custom separator"
        id="my-separator"
      />
    );

    const separator = screen.getByTestId('separator');
    expect(separator).toHaveAttribute('aria-label', 'Custom separator');
    expect(separator).toHaveAttribute('id', 'my-separator');
  });

  it('should render with both vertical orientation and decorative props', () => {
    render(
      <Separator orientation="vertical" decorative data-testid="separator" />
    );

    const separator = screen.getByTestId('separator');
    expect(separator.getAttribute('data-orientation')).toBe('vertical');
    expect(separator).toHaveAttribute('role', 'none');
    expect(separator.className).toContain('data-[orientation=vertical]:h-full');
    expect(separator.className).toContain('data-[orientation=vertical]:w-px');
  });
});
