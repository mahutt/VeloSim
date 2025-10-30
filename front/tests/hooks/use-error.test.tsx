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
import { renderHook } from '@testing-library/react';
import { ErrorProvider } from '~/providers/error-provider';
import type { ReactNode } from 'react';

// Wrapper component to provide context
const Wrapper = ({ children }: { children: ReactNode }) => (
  <ErrorProvider>{children}</ErrorProvider>
);

test('useError returns context when used within ErrorProvider', async () => {
  vi.doUnmock('~/hooks/use-error');
  const module = await import('~/hooks/use-error');
  const localUseError = module.default;
  const { result } = renderHook(() => localUseError(), {
    wrapper: Wrapper,
  });

  expect(result.current).toEqual({
    displayError: expect.any(Function),
  });
});

test('useError throws error when used outside ErrorProvider', async () => {
  vi.doUnmock('~/hooks/use-error');
  const module = await import('~/hooks/use-error');
  const localUseError = module.default;
  expect(() => {
    renderHook(() => localUseError());
  }).toThrow('useError must be used within an ErrorProvider');
});
