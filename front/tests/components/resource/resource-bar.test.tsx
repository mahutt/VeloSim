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
import { useSimulation } from '~/providers/simulation-provider';
import { SelectedItemType } from '~/types';
import ResourceBar from '~/components/resource/resource-bar';
import userEvent from '@testing-library/user-event';

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
vi.mock('~/providers/simulation-provider', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(typeof actual === 'object' && actual !== null ? actual : {}),
    useSimulation: vi.fn(),
  };
});

const mockResources = [
  {
    id: 1,
    position: [-73.57776, 45.48944] as [number, number],
    taskList: [1, 2, 3],
    route: {
      coordinates: [[-73.57776, 45.48944]] as [number, number][],
    },
  },
  {
    id: 2,
    position: [-73.58, 45.49] as [number, number],
    taskList: [4, 5],
    route: {
      coordinates: [[-73.58, 45.49]] as [number, number][],
    },
  },
  {
    id: 12,
    position: [-73.59, 45.5] as [number, number],
    taskList: [6],
    route: {
      coordinates: [[-73.59, 45.5]] as [number, number][],
    },
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

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
  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#2')).toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
});

test('renders search bar with correct placeholder', () => {
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
  expect(screen.getByPlaceholderText('Search Resource')).toBeInTheDocument();
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

test('filters resources by ID match', async () => {
  const user = userEvent.setup();
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

  const searchInput = screen.getByPlaceholderText('Search Resource');
  await user.type(searchInput, '1');

  // Should show resources with ID 1 and 12 (since both contain "1")
  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
  expect(screen.queryByText('#2')).not.toBeInTheDocument();
});

test('filters resources by partial ID match', async () => {
  const user = userEvent.setup();
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

  const searchInput = screen.getByPlaceholderText('Search Resource');
  await user.type(searchInput, '12');

  // Should only show resource that has ID 12
  expect(screen.queryByText('#1')).not.toBeInTheDocument();
  expect(screen.queryByText('#2')).not.toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
});

test('shows no resources when search query does not match any ID', async () => {
  const user = userEvent.setup();
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

  const searchInput = screen.getByPlaceholderText('Search Resource');
  await user.type(searchInput, '999');

  expect(screen.queryByText('#1')).not.toBeInTheDocument();
  expect(screen.queryByText('#2')).not.toBeInTheDocument();
  expect(screen.queryByText('#12')).not.toBeInTheDocument();
});

test('shows all resources when search query is empty', async () => {
  const user = userEvent.setup();
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

  const searchInput = screen.getByPlaceholderText('Search Resource');

  await user.type(searchInput, '1');
  expect(screen.queryByText('#2')).not.toBeInTheDocument();

  // Clear the input
  await user.clear(searchInput);

  // Should show all resources again
  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#2')).toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
});

test('clears search when clear button is clicked', async () => {
  const user = userEvent.setup();
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

  const searchInput = screen.getByPlaceholderText('Search Resource');

  await user.type(searchInput, '2');
  expect(screen.getByDisplayValue('2')).toBeInTheDocument();
  expect(screen.queryByText('#1')).not.toBeInTheDocument();
  expect(screen.getByText('#2')).toBeInTheDocument();

  // Click clear button
  const clearButton = screen.getByRole('button', { name: 'Clear search' });
  await user.click(clearButton);

  // Search should be cleared and all resources should be visible
  expect(screen.getByDisplayValue('')).toBeInTheDocument();
  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#2')).toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
});

test('search is case insensitive for partial matches', async () => {
  const user = userEvent.setup();
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

  const searchInput = screen.getByPlaceholderText('Search Resource');

  await user.type(searchInput, '1');
  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#12')).toBeInTheDocument();
});

test('maintains selection state while filtering', async () => {
  const user = userEvent.setup();
  const selectItem = vi.fn();
  const selectedResource = mockResources[0];

  (useSimulation as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    selectItem,
    resources: mockResources,
    stationsRef: { current: new Map() },
    resourcesRef: { current: new Map() },
    selectedItem: {
      type: SelectedItemType.Resource,
      value: selectedResource,
    },
    clearSelection: vi.fn(),
  });

  render(<ResourceBar />);

  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.getByText('#2')).toBeInTheDocument();

  const searchInput = screen.getByPlaceholderText('Search Resource');
  await user.type(searchInput, '1');

  expect(screen.getByText('#1')).toBeInTheDocument();
  expect(screen.queryByText('#2')).not.toBeInTheDocument();
});
