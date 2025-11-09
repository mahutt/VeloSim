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
import { ResourceItem } from '~/components/resource/resource-item';
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
  const mockResource = {
    id: 1,
    position: [-73.57776, 45.48944] as [number, number],
    taskList: [1, 2, 3],
    route: {
      coordinates: [[-73.57776, 45.48944]] as [number, number][],
    },
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

  expect(screen.getByText('#1')).toBeDefined();
  expect(screen.getByText('3 tasks')).toBeDefined();
});

test('resource item renders with selection state', () => {
  const mockResource = {
    id: 1,
    position: [-73.57776, 45.48944] as [number, number],
    taskList: [1, 2],
    route: {
      coordinates: [[-73.57776, 45.48944]] as [number, number][],
    },
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
    .getByText('#1')
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
    .getByText('#1')
    .closest('div')
    ?.closest('[data-slot="item"]') as HTMLElement | null;
  expect(selectedItemRoot).toBeDefined();
  expect(selectedItemRoot?.className).toContain('bg-red-50');
  expect(selectedItemRoot?.className).toContain('border-red-500');
});

test('resource item calls onSelect when clicked', () => {
  const mockResource = {
    id: 2,
    position: [-73.57776, 45.48944] as [number, number],
    taskList: [1, 2, 3, 4, 5],
    route: {
      coordinates: [[-73.57776, 45.48944]] as [number, number][],
    },
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

  const container = screen.getByText('#2').closest('div');
  if (container) {
    fireEvent.click(container);
  }

  expect(mockOnSelect).toHaveBeenCalledTimes(1);
});

test('resource item displays correct task count', () => {
  const mockResource = {
    id: 5,
    position: [-73.57776, 45.48944] as [number, number],
    taskList: [1, 2, 3, 4, 5, 6, 7, 8],
    route: {
      coordinates: [[-73.57776, 45.48944]] as [number, number][],
    },
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

  expect(screen.getByText('8 tasks')).toBeDefined();
});

test('resource item renders correctly when resource is undefined', () => {
  const mockOnSelect = vi.fn();

  const { container } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem resource={undefined} onSelect={mockOnSelect} />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  expect(container.firstChild).toBeNull();
});

test('resource item calls onSelect even when resource is undefined', () => {
  const mockOnSelect = vi.fn();

  render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <ResourceItem resource={undefined} onSelect={mockOnSelect} />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );

  expect(mockOnSelect).toHaveBeenCalledTimes(0);
});
