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

import { expect, test, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SearchBar } from '~/components/ui/search-bar';
import userEvent from '@testing-library/user-event';

test('renders search bar with placeholder text', () => {
  render(<SearchBar placeholder="Search resources" />);

  const input = screen.getByPlaceholderText('Search resources');
  expect(input).toBeInTheDocument();
  expect(input).toHaveAttribute('type', 'text');
});

test('renders search icon', () => {
  const { container } = render(<SearchBar />);

  const searchIcon = container.querySelector('svg');
  expect(searchIcon).toBeInTheDocument();
});

test('displays input value correctly', () => {
  render(<SearchBar value="test query" onChange={() => {}} />);

  const input = screen.getByDisplayValue('test query');
  expect(input).toBeInTheDocument();
});

test('calls onChange when typing in input', async () => {
  const user = userEvent.setup();
  const handleChange = vi.fn();

  render(<SearchBar onChange={handleChange} />);

  const input = screen.getByRole('textbox');
  await user.type(input, 'test');

  expect(handleChange).toHaveBeenCalledTimes(4);
});

test('shows clear button when value is provided', () => {
  render(<SearchBar value="test" onClear={() => {}} />);

  const clearButton = screen.getByRole('button', { name: 'Clear search' });
  expect(clearButton).toBeInTheDocument();
});

test('does not show clear button when value is empty', () => {
  render(<SearchBar value="" onClear={() => {}} />);

  const clearButton = screen.queryByRole('button', { name: 'Clear search' });
  expect(clearButton).not.toBeInTheDocument();
});

test('does not show clear button when value is undefined', () => {
  render(<SearchBar onClear={() => {}} />);

  const clearButton = screen.queryByRole('button', { name: 'Clear search' });
  expect(clearButton).not.toBeInTheDocument();
});

test('calls onClear when clear button is clicked', async () => {
  const user = userEvent.setup();
  const handleClear = vi.fn();

  render(<SearchBar value="test" onClear={handleClear} />);

  const clearButton = screen.getByRole('button', { name: 'Clear search' });
  await user.click(clearButton);

  expect(handleClear).toHaveBeenCalledTimes(1);
});

test('forwards ref to input element', () => {
  const ref = { current: null };

  render(<SearchBar ref={ref} />);

  expect(ref.current).toBeInstanceOf(HTMLInputElement);
});

test('applies custom className', () => {
  render(<SearchBar className="custom-class" />);

  const input = screen.getByRole('textbox');
  expect(input.className).toContain('custom-class');
});

test('applies default styling classes', () => {
  render(<SearchBar />);

  const input = screen.getByRole('textbox');
  expect(input).toHaveClass('h-9', 'w-full', 'rounded-full', 'border');
});

test('passes through additional props to input', () => {
  render(<SearchBar disabled data-testid="search-input" />);

  const input = screen.getByTestId('search-input');
  expect(input).toBeDisabled();
});

test('supports all standard input props except type', () => {
  const handleFocus = vi.fn();
  const handleBlur = vi.fn();

  render(
    <SearchBar
      autoComplete="off"
      maxLength={50}
      onFocus={handleFocus}
      onBlur={handleBlur}
      required
    />
  );

  const input = screen.getByRole('textbox');
  expect(input).toHaveAttribute('autocomplete', 'off');
  expect(input).toHaveAttribute('maxlength', '50');
  expect(input).toBeRequired();
});

test('handles focus and blur events', async () => {
  const user = userEvent.setup();
  const handleFocus = vi.fn();
  const handleBlur = vi.fn();

  render(<SearchBar onFocus={handleFocus} onBlur={handleBlur} />);

  const input = screen.getByRole('textbox');

  await user.click(input);
  expect(handleFocus).toHaveBeenCalledTimes(1);

  await user.tab();
  expect(handleBlur).toHaveBeenCalledTimes(1);
});

test('clear button has correct accessibility attributes', () => {
  render(<SearchBar value="test" onClear={() => {}} />);

  const clearButton = screen.getByRole('button', { name: 'Clear search' });
  expect(clearButton).toHaveAttribute('aria-label', 'Clear search');
  expect(clearButton).toHaveAttribute('tabIndex', '-1');
  expect(clearButton).toHaveAttribute('type', 'button');
});

test('clear button shows X icon', () => {
  render(<SearchBar value="test" onClear={() => {}} />);

  const clearButton = screen.getByRole('button', { name: 'Clear search' });
  const icon = clearButton.querySelector('svg');
  expect(icon).toBeInTheDocument();
});

test('handles keyboard events correctly', async () => {
  const user = userEvent.setup();
  const handleKeyDown = vi.fn();

  render(<SearchBar onKeyDown={handleKeyDown} />);

  const input = screen.getByRole('textbox');
  await user.type(input, '{enter}');

  expect(handleKeyDown).toHaveBeenCalled();
});

test('clear button hover styles are applied', () => {
  render(<SearchBar value="test" onClear={() => {}} />);

  const clearButton = screen.getByRole('button', { name: 'Clear search' });
  expect(clearButton).toHaveClass('hover:text-foreground', 'transition-colors');
});

test('search icon is positioned correctly', () => {
  const { container } = render(<SearchBar />);

  const searchIconContainer = container.querySelector('.absolute.left-3');
  expect(searchIconContainer).toBeInTheDocument();
  expect(searchIconContainer).toHaveClass(
    'top-1/2',
    '-translate-y-1/2',
    'pointer-events-none'
  );
});
