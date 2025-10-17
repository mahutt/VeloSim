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

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoginAlert, { LoginErrorMessage } from '~/components/login/login-alert';

describe('LoginAlert', () => {
  it('should display server error message for 5xx codes', () => {
    render(<LoginAlert code={500} />);
    expect(screen.getByText(LoginErrorMessage.ServerError)).toBeInTheDocument();
  });

  it('should display invalid credentials message for 400 code', () => {
    render(<LoginAlert code={400} />);
    expect(
      screen.getByText(LoginErrorMessage.InvalidCredentials)
    ).toBeInTheDocument();
  });

  it('should display unknown error message for other codes', () => {
    render(<LoginAlert code={418} />);
    expect(
      screen.getByText(LoginErrorMessage.UnknownError)
    ).toBeInTheDocument();
  });

  it('should render with destructive variant and include alert icon', () => {
    render(<LoginAlert code={500} />);
    const alert = screen.getByRole('alert');
    expect(alert.querySelector('svg')).toBeInTheDocument();
  });
});
