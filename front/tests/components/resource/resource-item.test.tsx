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
import {
  ResourceItem,
  type ResourceItemElement,
} from '~/components/resource/resource-item';
import { MapProvider } from '~/providers/map-provider';
import { SimulationProvider } from '~/providers/simulation-provider';
import { TaskAssignmentProvider } from '~/providers/task-assignment-provider';

// Mock useAuth hook
vi.mock('~/hooks/use-auth', () => ({
  default: () => ({
    user: { id: 1, username: 'test_user', is_admin: false },
    setUser: vi.fn(),
    loading: false,
    setLoading: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    setToken: vi.fn(),
  }),
}));

test('resource item renders with resource data', () => {
  const mockResource: ResourceItemElement = {
    id: 1,
    name: 'John Doe',
    taskCount: 3,
    batteryCount: 1,
    batteryCapacity: 100,
  };

  const mockOnSelect = vi.fn();

  render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem resource={mockResource} onSelect={mockOnSelect} />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  expect(screen.getByText('John Doe')).toBeDefined();
  expect(screen.getByText('#1')).toBeDefined();
});

test('resource item renders with selection state', () => {
  const mockResource: ResourceItemElement = {
    id: 1,
    name: 'Jane Smith',
    taskCount: 5,
    batteryCount: 0,
    batteryCapacity: 100,
  };

  const mockOnSelect = vi.fn();

  const { rerender } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem
            resource={mockResource}
            onSelect={mockOnSelect}
            isSelected={false}
          />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  // Check unselected state styling
  const itemRoot = screen
    .getByText('Jane Smith')
    .closest('div')
    ?.closest('[data-slot="item"]') as HTMLElement | null;
  expect(itemRoot).toBeDefined();
  expect(itemRoot?.className).toContain('bg-white');
  expect(itemRoot?.className).not.toContain('bg-red-50');

  // Rerender with selected state
  rerender(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem
            resource={mockResource}
            onSelect={mockOnSelect}
            isSelected={true}
          />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  const selectedItemRoot = screen
    .getByText('Jane Smith')
    .closest('div')
    ?.closest('[data-slot="item"]') as HTMLElement | null;
  expect(selectedItemRoot).toBeDefined();
  expect(selectedItemRoot?.className).toContain('bg-red-50');
  expect(selectedItemRoot?.className).toContain('border-red-500');
});

test('resource item calls onSelect when clicked', () => {
  const mockResource: ResourceItemElement = {
    id: 2,
    name: 'Bob Johnson',
    taskCount: 5,
    batteryCount: 2,
    batteryCapacity: 100,
  };

  const mockOnSelect = vi.fn();

  render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem resource={mockResource} onSelect={mockOnSelect} />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  const container = screen.getByText('Bob Johnson').closest('div');
  if (container) {
    fireEvent.click(container);
  }

  expect(mockOnSelect).toHaveBeenCalledTimes(1);
});

test('resource item displays driver name and ID', () => {
  const mockResource: ResourceItemElement = {
    id: 3,
    name: 'Charlie Brown',
    taskCount: 2,
    batteryCount: 1,
    batteryCapacity: 100,
  };

  const mockOnSelect = vi.fn();

  render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem resource={mockResource} onSelect={mockOnSelect} />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  expect(screen.getByText('Charlie Brown')).toBeDefined();
  expect(screen.getByText('#3')).toBeDefined();
});

test('resource item displays battery status indicator', () => {
  const mockResource: ResourceItemElement = {
    id: 4,
    name: 'Diana Prince',
    taskCount: 1,
    batteryCount: 2,
    batteryCapacity: 100,
  };

  const mockOnSelect = vi.fn();

  render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem resource={mockResource} onSelect={mockOnSelect} />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  expect(screen.getByText('2')).toBeDefined();
});
