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
import { render, screen, fireEvent } from '@testing-library/react';
import { useSimulation } from '~/providers/simulation-provider';
import { SelectedItemType } from '~/types';
import ResourceBar from '~/components/resource/resource-bar';

// Mock ResourceItem to simplify rendering
vi.mock('~/components/resource/resource-item', () => ({
  ResourceItem: ({
    resource,
    onSelect,
  }: {
    resource: { name: string };
    onSelect: () => void;
  }) => (
    <div data-testid="resource-item" onClick={onSelect}>
      {resource.name}
    </div>
  ),
}));

// Mock useSimulation
vi.mock('~/providers/simulation-provider', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(typeof actual === 'object' && actual !== null ? actual : {}),
    useSimulation: vi.fn(),
  };
});

const mockResources = [
  { id: 1, name: 'Resource A' },
  { id: 2, name: 'Resource B' },
];

test('should throw error when used outside provider', () => {
  const mockUseSimulation = useSimulation as unknown as ReturnType<
    typeof vi.fn
  >;
  mockUseSimulation.mockImplementation(() => {
    throw new Error('useSimulation must be used within a SimulationProvider');
  });

  expect(() => {
    render(<ResourceBar />);
  }).toThrow('useSimulation must be used within a SimulationProvider');
});

test('renders all resources from provider', () => {
  const selectItem = vi.fn();
  (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    selectItem,
    resources: mockResources,
    stationsRef: { current: new Map() },
    resourcesRef: { current: new Map() },
    selectedItem: null,
    clearSelection: vi.fn(),
  });

  render(<ResourceBar />);
  expect(screen.getAllByTestId('resource-item')).toHaveLength(
    mockResources.length
  );
  expect(screen.getByText('Resource A')).toBeInTheDocument();
  expect(screen.getByText('Resource B')).toBeInTheDocument();
});

test('calls selectItem with correct arguments when resource is clicked', () => {
  const selectItem = vi.fn();
  (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    selectItem,
    resources: mockResources,
    stationsRef: { current: new Map() },
    resourcesRef: { current: new Map() },
    selectedItem: null,
    clearSelection: vi.fn(),
  });

  render(<ResourceBar />);
  const items = screen.getAllByTestId('resource-item');
  fireEvent.click(items[0]);
  expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Resource, 1);
  fireEvent.click(items[1]);
  expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Resource, 2);
});
