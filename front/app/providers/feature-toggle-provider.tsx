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

import React, {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import {
  DEFAULT_FLAGS,
  FEATURE_FLAGS_KEY,
  parseFlags,
} from '~/utils/feature-flags';
import type { FeatureFlags } from '~/utils/feature-flags';

export interface FeatureToggleState {
  flags: FeatureFlags;
  isEnabled: (k: keyof FeatureFlags) => boolean;
  setOverride: (partial: Partial<FeatureFlags>) => void;
  refreshFromRemote: () => Promise<void>;
}

export const FeatureToggleContext = createContext<
  FeatureToggleState | undefined
>(undefined);

interface FeatureToggleProviderProps {
  children: ReactNode;
}

async function fetchAndMergeFlags(): Promise<FeatureFlags> {
  try {
    const res = await fetch('/feature-flags.json', { cache: 'no-store' });
    let remote: Partial<FeatureFlags> = {};
    if (res.ok) {
      remote = await res.json();
    }
    const override = parseFlags(sessionStorage.getItem(FEATURE_FLAGS_KEY));
    return { ...DEFAULT_FLAGS, ...remote, ...override } as FeatureFlags;
  } catch {
    const override = parseFlags(sessionStorage.getItem(FEATURE_FLAGS_KEY));
    return { ...DEFAULT_FLAGS, ...override } as FeatureFlags;
  }
}

export const FeatureToggleProvider: React.FC<FeatureToggleProviderProps> = ({
  children,
}) => {
  const [flags, setFlags] = useState<FeatureFlags>(
    () => ({ ...DEFAULT_FLAGS }) as FeatureFlags
  );

  const refreshFromRemote = useCallback(async () => {
    const merged = await fetchAndMergeFlags();
    setFlags(merged);
  }, []);

  useEffect(() => {
    void refreshFromRemote();
  }, [refreshFromRemote]);

  const setOverride = useCallback(
    (partial: Partial<FeatureFlags>) => {
      try {
        const existing = parseFlags(sessionStorage.getItem(FEATURE_FLAGS_KEY));
        const newOverride = { ...existing, ...partial };
        sessionStorage.setItem(FEATURE_FLAGS_KEY, JSON.stringify(newOverride));
        const merged = { ...flags, ...partial } as FeatureFlags;
        setFlags(merged);
      } catch (err) {
        console.warn(err);
      }
    },
    [flags]
  );

  const isEnabled = useCallback((k: keyof FeatureFlags) => !!flags[k], [flags]);

  const value: FeatureToggleState = {
    flags,
    isEnabled,
    setOverride,
    refreshFromRemote,
  };

  return (
    <FeatureToggleContext.Provider value={value}>
      {children}
    </FeatureToggleContext.Provider>
  );
};
