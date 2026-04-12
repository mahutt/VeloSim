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

import { beforeEach, expect, test, vi } from 'vitest';
import { render, act, renderHook } from '@testing-library/react';
import {
  SimulationProvider,
  useSimulation,
} from '~/providers/simulation-provider';
import {
  PreferencesContext,
  PreferencesProvider,
} from '~/providers/preferences-provider';
import type { AuthState } from '~/providers/auth-provider';
import { DEFAULT_REACTIVE_SIMULATION_STATE } from '~/lib/reactive-simulation-state';
import type { Map } from 'mapbox-gl';
import { mockSimulationEngine } from 'tests/mocks';
import { useContext } from 'react';
import api from '~/api';
import useAuth from '~/hooks/use-auth';
import { DEFAULT_UI_LANGUAGE, USER_PREFERENCES_STORAGE_KEY } from '~/constants';
import { UILanguage } from '~/types';

const { MockSimulationEngine } = await vi.hoisted(() => import('tests/mocks'));
vi.mock('~/lib/simulation-engine', () => {
  return {
    default: MockSimulationEngine,
  };
});
vi.mock('~/hooks/use-auth', () => ({
  default: vi.fn(),
}));
vi.mock('~/api', () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

const mockMap = {} as Map;

beforeEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

test('SimulationProvider instantiates SimulationEngine with correct arguments', () => {
  const simulationId = 'sim-123';
  render(
    <SimulationProvider simulationId={simulationId} map={mockMap}>
      <div />
    </SimulationProvider>
  );

  expect(MockSimulationEngine).toHaveBeenCalledOnce();
  expect(MockSimulationEngine).toHaveBeenCalledWith(
    simulationId,
    mockMap,
    expect.objectContaining(DEFAULT_REACTIVE_SIMULATION_STATE),
    expect.any(Function)
  );
});

test('destroy is called on unmount when engine has started', () => {
  mockSimulationEngine.hasStarted = vi.fn().mockReturnValue(true);

  const { unmount } = render(
    <SimulationProvider simulationId="sim-789" map={mockMap}>
      <div />
    </SimulationProvider>
  );

  act(() => {
    unmount();
  });

  expect(mockSimulationEngine.destroy).toHaveBeenCalledOnce();
});

test('useSimulation returns state and engine from context', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <SimulationProvider simulationId="sim-456" map={mockMap}>
      {children}
    </SimulationProvider>
  );

  const { result } = renderHook(() => useSimulation(), { wrapper });

  expect(result.current.state).toMatchObject(DEFAULT_REACTIVE_SIMULATION_STATE);
  expect(result.current.engine).toBeDefined();
});

test('useSimulation throws error when used outside SimulationProvider', () => {
  expect(() => {
    renderHook(() => useSimulation());
  }).toThrow('useSimulation must be used within a SimulationProvider');
});

test('PreferencesProvider uses session storage when no authenticated user', async () => {
  sessionStorage.setItem(
    USER_PREFERENCES_STORAGE_KEY,
    JSON.stringify({ language: UILanguage.French })
  );
  vi.mocked(useAuth).mockReturnValue({
    user: null,
    loading: false,
  } as unknown as AuthState);

  let ctx: React.ContextType<typeof PreferencesContext>;
  function Capture() {
    ctx = useContext(PreferencesContext);
    return null;
  }

  render(
    <PreferencesProvider>
      <Capture />
    </PreferencesProvider>
  );

  await act(async () => {
    await Promise.resolve();
  });

  expect(ctx!).toBeDefined();
  expect(ctx!.language).toBe(UILanguage.French);
  expect(document.documentElement.lang).toBe(UILanguage.French);
});

test('PreferencesProvider refreshes and updates preferences for authenticated user', async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 42 },
    loading: false,
  } as unknown as AuthState);
  vi.mocked(api.get).mockResolvedValue({
    data: { language: UILanguage.English },
  } as never);
  vi.mocked(api.patch).mockResolvedValue({
    data: { language: UILanguage.French },
  } as never);

  let ctx: React.ContextType<typeof PreferencesContext>;
  function Capture() {
    ctx = useContext(PreferencesContext);
    return null;
  }

  render(
    <PreferencesProvider>
      <Capture />
    </PreferencesProvider>
  );

  await act(async () => {
    await Promise.resolve();
  });

  expect(api.get).toHaveBeenCalledWith('/users/me/preferences');
  expect(ctx!.language).toBe(UILanguage.English);

  await act(async () => {
    await ctx!.setLanguagePreference(UILanguage.French);
  });

  expect(api.patch).toHaveBeenCalledWith('/users/me/preferences', {
    language: UILanguage.French,
  });
  expect(ctx!.language).toBe(UILanguage.French);
});

test('PreferencesProvider falls back to default language when storage payload is invalid', async () => {
  sessionStorage.setItem(USER_PREFERENCES_STORAGE_KEY, '{invalid-json');
  vi.mocked(useAuth).mockReturnValue({
    user: null,
    loading: false,
  } as unknown as AuthState);

  let ctx: React.ContextType<typeof PreferencesContext>;
  function Capture() {
    ctx = useContext(PreferencesContext);
    return null;
  }

  render(
    <PreferencesProvider>
      <Capture />
    </PreferencesProvider>
  );

  await act(async () => {
    await Promise.resolve();
  });

  expect(ctx!.language).toBe(DEFAULT_UI_LANGUAGE);
});

test('PreferencesProvider falls back to stored preferences when remote refresh fails', async () => {
  sessionStorage.setItem(
    USER_PREFERENCES_STORAGE_KEY,
    JSON.stringify({ language: UILanguage.French })
  );
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 7 },
    loading: false,
  } as unknown as AuthState);
  vi.mocked(api.get).mockRejectedValue(new Error('network'));

  let ctx: React.ContextType<typeof PreferencesContext>;
  function Capture() {
    ctx = useContext(PreferencesContext);
    return null;
  }

  render(
    <PreferencesProvider>
      <Capture />
    </PreferencesProvider>
  );

  await act(async () => {
    await Promise.resolve();
  });

  expect(ctx!.language).toBe(UILanguage.French);
});

test('PreferencesProvider does not patch when user is unauthenticated', async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: null,
    loading: false,
  } as unknown as AuthState);

  let ctx: React.ContextType<typeof PreferencesContext>;
  function Capture() {
    ctx = useContext(PreferencesContext);
    return null;
  }

  render(
    <PreferencesProvider>
      <Capture />
    </PreferencesProvider>
  );

  await act(async () => {
    await Promise.resolve();
    await ctx!.setLanguagePreference(UILanguage.French);
  });

  expect(api.patch).not.toHaveBeenCalled();
});

test('PreferencesProvider keeps saving false after patch error', async () => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 11 },
    loading: false,
  } as unknown as AuthState);
  vi.mocked(api.get).mockResolvedValue({
    data: { language: UILanguage.English },
  } as never);
  vi.mocked(api.patch).mockRejectedValue(new Error('patch failed'));

  let ctx: React.ContextType<typeof PreferencesContext>;
  function Capture() {
    ctx = useContext(PreferencesContext);
    return null;
  }

  render(
    <PreferencesProvider>
      <Capture />
    </PreferencesProvider>
  );

  await act(async () => {
    await Promise.resolve();
  });

  await expect(ctx!.setLanguagePreference(UILanguage.French)).rejects.toThrow(
    'patch failed'
  );
  expect(ctx!.saving).toBe(false);
});
