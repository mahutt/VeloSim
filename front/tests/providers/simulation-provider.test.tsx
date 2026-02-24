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
import { render, act, renderHook } from '@testing-library/react';
import {
  SimulationProvider,
  useSimulation,
} from '~/providers/simulation-provider';
import { DEFAULT_REACTIVE_SIMULATION_STATE } from '~/lib/reactive-simulation-state';
import type { Map } from 'mapbox-gl';
import { mockSimulationEngine } from 'tests/mocks';

const { MockSimulationEngine } = await vi.hoisted(() => import('tests/mocks'));
vi.mock('~/lib/simulation-engine', () => {
  return {
    default: MockSimulationEngine,
  };
});

const mockMap = {} as Map;

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
