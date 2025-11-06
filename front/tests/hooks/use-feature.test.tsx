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

import { describe, expect, test, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useFeature } from '~/hooks/use-feature';
import { FeatureToggleProvider } from '~/providers/feature-toggle-provider';
import { DEFAULT_FLAGS, FEATURE_FLAGS_KEY } from '~/utils/feature-flags';
import type { ReactNode } from 'react';

function createWrapper() {
  function Wrapper({ children }: { children: ReactNode }) {
    return <FeatureToggleProvider>{children}</FeatureToggleProvider>;
  }

  Wrapper.displayName = 'FeatureToggleProviderWrapper';

  return Wrapper;
}

describe('useFeature', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  test('returns default flag value', async () => {
    const { result } = renderHook(() => useFeature('sidebar'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current).toBe(DEFAULT_FLAGS.sidebar);
    });
  });

  test('returns true for enabled feature', async () => {
    sessionStorage.setItem(
      FEATURE_FLAGS_KEY,
      JSON.stringify({ taskDragAndDrop: true })
    );

    const { result } = renderHook(() => useFeature('taskDragAndDrop'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  test('returns false for disabled feature', async () => {
    sessionStorage.setItem(
      FEATURE_FLAGS_KEY,
      JSON.stringify({ sidebar: false })
    );

    const { result } = renderHook(() => useFeature('sidebar'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current).toBe(false);
    });
  });

  test('returns value for simulationsPage flag', async () => {
    const { result } = renderHook(() => useFeature('simulationsPage'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current).toBe(DEFAULT_FLAGS.simulationsPage);
    });
  });

  test('updates when flags change', async () => {
    const { result, rerender } = renderHook(() => useFeature('sidebar'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current).toBe(DEFAULT_FLAGS.sidebar);
    });

    sessionStorage.setItem(
      FEATURE_FLAGS_KEY,
      JSON.stringify({ sidebar: false })
    );

    rerender();
  });

  test('throws error when used outside provider', () => {
    // ignore console.error for this test since error is expected
    const originalError = console.error;
    console.error = () => {};

    expect(() => {
      renderHook(() => useFeature('sidebar'));
    }).toThrow();

    console.error = originalError;
  });

  test('handles all feature flag types', async () => {
    const flags = ['sidebar', 'taskDragAndDrop', 'simulationsPage'] as const;

    for (const flag of flags) {
      const { result } = renderHook(() => useFeature(flag), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(typeof result.current).toBe('boolean');
      });
    }
  });
});
