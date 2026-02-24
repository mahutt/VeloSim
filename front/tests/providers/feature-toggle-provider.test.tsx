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

import { describe, expect, test, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import {
  FeatureToggleProvider,
  FeatureToggleContext,
  type FeatureToggleState,
} from '~/providers/feature-toggle-provider';
import { DEFAULT_FLAGS, FEATURE_FLAGS_KEY } from '~/utils/feature-flags';
import { useContext } from 'react';

function TestConsumer() {
  const context = useContext(FeatureToggleContext);

  if (!context) {
    return <div>No context</div>;
  }

  const { flags, isEnabled, setOverride, refreshFromRemote } = context;

  return (
    <div>
      <div data-testid="sidebar-flag">{String(flags.sidebar)}</div>
      <div data-testid="simulations-flag">{String(flags.simulationsPage)}</div>
      <div data-testid="sidebar-enabled">{String(isEnabled('sidebar'))}</div>
      <button
        onClick={() => setOverride({ sidebar: false })}
        data-testid="toggle-sidebar"
      >
        Toggle Sidebar
      </button>
      <button onClick={() => refreshFromRemote()} data-testid="refresh-flags">
        Refresh
      </button>
    </div>
  );
}

describe('FeatureToggleProvider', () => {
  beforeEach(() => {
    // clear sessionStorage before each test
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  test('provides default flags on initial render', async () => {
    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent(
        String(DEFAULT_FLAGS.sidebar)
      );
      expect(screen.getByTestId('simulations-flag')).toHaveTextContent(
        String(DEFAULT_FLAGS.simulationsPage)
      );
    });
  });

  test('isEnabled returns correct boolean values', async () => {
    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-enabled')).toHaveTextContent(
        String(DEFAULT_FLAGS.sidebar)
      );
    });
  });

  test('loads flags from sessionStorage on mount', async () => {
    const overrideFlags = {
      sidebar: false,
      taskDragAndDrop: true,
    };
    sessionStorage.setItem(FEATURE_FLAGS_KEY, JSON.stringify(overrideFlags));

    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent('false');
      // simulationsPage should still be default since not overridden
      expect(screen.getByTestId('simulations-flag')).toHaveTextContent(
        String(DEFAULT_FLAGS.simulationsPage)
      );
    });
  });

  test('setOverride updates flags and sessionStorage', async () => {
    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent(
        String(DEFAULT_FLAGS.sidebar)
      );
    });

    await act(async () => {
      screen.getByTestId('toggle-sidebar').click();
    });

    // check that the flag was updated
    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent('false');
    });

    // check that sessionStorage was updated
    const stored = sessionStorage.getItem(FEATURE_FLAGS_KEY);
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.sidebar).toBe(false);
  });

  test('setOverride merges with existing overrides', async () => {
    // set initial override
    sessionStorage.setItem(
      FEATURE_FLAGS_KEY,
      JSON.stringify({ simulationsPage: false })
    );

    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('simulations-flag')).toHaveTextContent('false');
    });

    // add another override
    await act(async () => {
      screen.getByTestId('toggle-sidebar').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent('false');
    });

    const stored = sessionStorage.getItem(FEATURE_FLAGS_KEY);
    const parsed = JSON.parse(stored!);
    expect(parsed.simulationsPage).toBe(false);
    expect(parsed.sidebar).toBe(false);
  });

  test('refreshFromRemote reloads flags from sessionStorage', async () => {
    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent(
        String(DEFAULT_FLAGS.sidebar)
      );
    });

    // manually update sessionStorage
    sessionStorage.setItem(
      FEATURE_FLAGS_KEY,
      JSON.stringify({ sidebar: false, taskDragAndDrop: true })
    );

    // trigger refresh
    await act(async () => {
      screen.getByTestId('refresh-flags').click();
    });

    // ensure flags were reloaded
    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent('false');
    });
  });

  test('handles invalid JSON in sessionStorage gracefully', async () => {
    sessionStorage.setItem(FEATURE_FLAGS_KEY, 'invalid json');

    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toHaveTextContent(
        String(DEFAULT_FLAGS.sidebar)
      );
    });
  });

  test('context provides all required methods', async () => {
    let capturedContext: FeatureToggleState | undefined;

    function ContextCapture() {
      capturedContext = useContext(FeatureToggleContext);
      return null;
    }

    render(
      <FeatureToggleProvider>
        <ContextCapture />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(capturedContext).toBeDefined();
      expect(capturedContext?.flags).toBeDefined();
      expect(typeof capturedContext?.isEnabled).toBe('function');
      expect(typeof capturedContext?.setOverride).toBe('function');
      expect(typeof capturedContext?.refreshFromRemote).toBe('function');
    });
  });

  test('isEnabled returns false for falsy values', async () => {
    sessionStorage.setItem(
      FEATURE_FLAGS_KEY,
      JSON.stringify({ sidebar: false })
    );

    let isEnabledResult: boolean | undefined;

    function TestIsEnabled() {
      const context = useContext(FeatureToggleContext);
      if (context) {
        isEnabledResult = context.isEnabled('sidebar');
      }
      return null;
    }

    render(
      <FeatureToggleProvider>
        <TestIsEnabled />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(isEnabledResult).toBe(false);
    });
  });

  test('multiple setOverride calls are handled correctly', async () => {
    render(
      <FeatureToggleProvider>
        <TestConsumer />
      </FeatureToggleProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('sidebar-flag')).toBeDefined();
    });

    await act(async () => {
      screen.getByTestId('toggle-sidebar').click();
      screen.getByTestId('toggle-sidebar').click();
      screen.getByTestId('toggle-sidebar').click();
    });

    const stored = sessionStorage.getItem(FEATURE_FLAGS_KEY);
    expect(stored).toBeTruthy();
  });
});
