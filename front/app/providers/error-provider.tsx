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

import React, { createContext, useState, type ReactNode } from 'react';
import ErrorDialog from '~/components/error-dialog';

const DEFAULT_ERROR_TITLE = 'Error';
const DEFAULT_ERROR_MESSAGE = 'An error has occurred.';

export interface ErrorState {
  displayError: (
    title?: string,
    message?: string,
    retryCallback?: () => void
  ) => void;
}

const ErrorContext = createContext<ErrorState | undefined>(undefined);

interface ErrorProviderProps {
  children: ReactNode;
}

export const ErrorProvider: React.FC<ErrorProviderProps> = ({ children }) => {
  const [errorTitle, setErrorTitle] = useState<string>(DEFAULT_ERROR_TITLE);
  const [errorMessage, setErrorMessage] = useState<string>(
    DEFAULT_ERROR_MESSAGE
  );
  const [retryCallback, setRetryCallback] = useState<(() => void) | undefined>(
    undefined
  );
  const [isErrorOpen, setIsErrorOpen] = useState<boolean>(false);

  const displayError = (
    title?: string,
    message?: string,
    retryCallback?: () => void
  ) => {
    setErrorTitle(title || DEFAULT_ERROR_TITLE);
    setErrorMessage(message || DEFAULT_ERROR_MESSAGE);
    setRetryCallback(() => retryCallback);
    setIsErrorOpen(true);
  };

  const value: ErrorState = {
    displayError,
  };

  return (
    <ErrorContext.Provider value={value}>
      {children}
      <ErrorDialog
        title={errorTitle}
        message={errorMessage}
        retryCallback={retryCallback}
        open={isErrorOpen}
        onOpenChange={setIsErrorOpen}
      />
    </ErrorContext.Provider>
  );
};

export { ErrorContext };
