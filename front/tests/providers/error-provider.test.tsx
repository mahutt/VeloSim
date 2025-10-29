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
import { ErrorProvider, ErrorContext } from '~/providers/error-provider';
import { useContext } from 'react';
import userEvent from '@testing-library/user-event';

// Test component to access context values
const TestComponent = () => {
  const errorContext = useContext(ErrorContext);
  if (!errorContext) throw new Error('ErrorContext is undefined');
  return (
    <div>
      <button
        data-testid="trigger-error"
        onClick={() => errorContext.displayError()}
      >
        Trigger Error
      </button>
      <button
        data-testid="trigger-custom-error"
        onClick={() =>
          errorContext.displayError('Custom Title', 'Custom Message')
        }
      >
        Trigger Custom Error
      </button>
      <button
        data-testid="trigger-error-with-retry"
        onClick={() =>
          errorContext.displayError('Retry Title', 'Retry Message', () =>
            console.log('retry')
          )
        }
      >
        Trigger Error With Retry
      </button>
    </div>
  );
};

test('provides initial state with dialog closed', () => {
  render(
    <ErrorProvider>
      <TestComponent />
    </ErrorProvider>
  );

  // Assert error dialog is closed by checking for data-testid="error-dialog"
  expect(screen.queryByTestId('error-dialog')).not.toBeInTheDocument();
});

test('displays error with default title and message', async () => {
  const user = userEvent.setup();

  render(
    <ErrorProvider>
      <TestComponent />
    </ErrorProvider>
  );

  await user.click(screen.getByTestId('trigger-error'));

  expect(screen.queryByTestId('error-dialog')).toBeInTheDocument();
  expect(screen.getByTestId('error-dialog-title').textContent).toBe('Error');
  expect(screen.getByText('An error has occurred.')).toBeInTheDocument();

  expect(screen.queryByTestId('error-dialog-retry')).not.toBeInTheDocument();
});

test('displays error with custom title and message', async () => {
  const user = userEvent.setup();

  render(
    <ErrorProvider>
      <TestComponent />
    </ErrorProvider>
  );

  await user.click(screen.getByTestId('trigger-custom-error'));

  expect(screen.queryByTestId('error-dialog')).toBeInTheDocument();
  expect(screen.getByTestId('error-dialog-title').textContent).toBe(
    'Custom Title'
  );

  expect(screen.getByText('Custom Message')).toBeInTheDocument();

  expect(screen.queryByTestId('error-dialog-retry')).not.toBeInTheDocument();
});

test('displays error with retry callback', async () => {
  const user = userEvent.setup();
  const retryFn = vi.fn();

  const TestWithRetry = () => {
    const errorContext = useContext(ErrorContext);
    if (!errorContext) throw new Error('ErrorContext is undefined');
    return (
      <button
        data-testid="trigger-retry"
        onClick={() =>
          errorContext.displayError('Retry Title', 'Retry Message', retryFn)
        }
      >
        Trigger
      </button>
    );
  };

  render(
    <ErrorProvider>
      <TestWithRetry />
    </ErrorProvider>
  );

  await user.click(screen.getByTestId('trigger-retry'));

  expect(screen.getByTestId('error-dialog-retry')).toBeInTheDocument();

  await user.click(screen.getByText('Retry'));

  expect(retryFn).toHaveBeenCalledTimes(1);
  expect(screen.queryByTestId('error-dialog')).not.toBeInTheDocument();
});

test('closes dialog when onOpenChange is called', async () => {
  const user = userEvent.setup();

  render(
    <ErrorProvider>
      <TestComponent />
    </ErrorProvider>
  );

  await user.click(screen.getByTestId('trigger-error'));
  expect(screen.queryByTestId('error-dialog')).toBeInTheDocument();

  await user.click(screen.getByTestId('error-dialog-close'));
  expect(screen.queryByTestId('error-dialog')).not.toBeInTheDocument();
});
