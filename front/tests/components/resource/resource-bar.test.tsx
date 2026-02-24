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
import { render, screen, fireEvent } from '@testing-library/react';
import {
  useSimulation,
  type SimulationContextType,
} from '~/providers/simulation-provider';
import ResourceBar, {
  type ResourceBarElement,
} from '~/components/resource/resource-bar';
import { SelectedItemType } from '~/components/map/selected-item-bar';
import type SimulationEngine from '~/lib/simulation-engine';
import { makeResourceItemElement } from 'tests/test-helpers';

// Mock ResourceItem to simplify rendering
vi.mock('~/components/resource/resource-item', () => ({
  ResourceItem: ({
    resource,
    onSelect,
  }: {
    resource: { id: number };
    onSelect: () => void;
  }) => (
    <div data-testid="resource-item" onClick={onSelect}>
      {resource ? `#${resource.id}` : ''}
    </div>
  ),
}));

// Mock useSimulation
const { mockUseSimulation } = await vi.hoisted(async () => {
  const { mockSimulationEngine } = await import('tests/mocks');
  const { DEFAULT_REACTIVE_SIMULATION_STATE } =
    await import('app/lib/reactive-simulation-state');
  const mockUseSimulationResult: SimulationContextType = {
    state: DEFAULT_REACTIVE_SIMULATION_STATE,
    engine: mockSimulationEngine as SimulationEngine,
  };
  const mockUseSimulation = () => mockUseSimulationResult;
  return { mockUseSimulation };
});

vi.mock(import('~/providers/simulation-provider'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useSimulation: mockUseSimulation,
  };
});

const mockResourceBarElement: ResourceBarElement = [
  makeResourceItemElement({ id: 1 }),
  makeResourceItemElement({ id: 2 }),
  makeResourceItemElement({ id: 12 }),
];

beforeEach(() => {
  vi.clearAllMocks();
});

test('renders all resources from provider', () => {
  useSimulation().state.resourceBarElement = mockResourceBarElement;

  render(<ResourceBar />);
  expect(screen.getAllByTestId('resource-item')).toHaveLength(
    mockResourceBarElement.length
  );
  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#2')).toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
});

test('calls selectItem with correct arguments when resource is clicked', () => {
  useSimulation().state.resourceBarElement = mockResourceBarElement;

  render(<ResourceBar />);
  const items = screen.getAllByTestId('resource-item');
  fireEvent.click(items[0]);
  expect(useSimulation().engine.selectItem).toHaveBeenCalledWith(
    SelectedItemType.Driver,
    1
  );
  fireEvent.click(items[1]);
  expect(useSimulation().engine.selectItem).toHaveBeenCalledWith(
    SelectedItemType.Driver,
    2
  );
});

test('shows "No resources currently available" when resources array is empty', () => {
  useSimulation().state.resourceBarElement = [];

  render(<ResourceBar />);
  expect(
    screen.getByText('No resources currently available')
  ).toBeInTheDocument();
});
