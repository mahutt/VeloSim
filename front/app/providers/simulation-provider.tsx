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

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  DEFAULT_REACTIVE_SIMULATION_STATE,
  type ReactiveSimulationState,
} from '~/lib/reactive-simulation-state';
import SimulationEngine from '~/lib/simulation-engine';
import type { Map } from 'mapbox-gl';

export const SPEED_OPTIONS = [0, 0.5, 1, 2, 4, 8] as const;
export type Speed = (typeof SPEED_OPTIONS)[number];
export type NonZeroSpeed = Exclude<Speed, 0>;

export type SimulationContextType = {
  state: ReactiveSimulationState;
  engine: SimulationEngine;
};

const SimulationContext = createContext<SimulationContextType | undefined>(
  undefined
);

interface SimulationProviderProps {
  simulationId: string;
  map: Map;
  children: ReactNode;
}

export const SimulationProvider = ({
  simulationId,
  map,
  children,
}: SimulationProviderProps) => {
  const [state, setState] = useState<ReactiveSimulationState>({
    ...DEFAULT_REACTIVE_SIMULATION_STATE,
  });
  const engineRef = useRef<SimulationEngine | null>(null);
  if (!engineRef.current) {
    engineRef.current = new SimulationEngine(
      simulationId,
      map,
      state,
      setState
    );
  }

  useEffect(() => {
    return () => {
      if (engineRef.current && engineRef.current.hasStarted()) {
        engineRef.current.destroy();
      }
    };
  }, []);

  return (
    <SimulationContext.Provider
      value={{
        state,
        engine: engineRef.current,
      }}
    >
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = (): SimulationContextType => {
  const context = useContext(SimulationContext);
  if (!context) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
};
