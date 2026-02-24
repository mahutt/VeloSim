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
import { type SimulationContextType } from '~/providers/simulation-provider';
import { makeResourceItemElement } from 'tests/test-helpers';
import type SimulationEngine from '~/lib/simulation-engine';

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

test('resource item renders with resource data', () => {
  const mockResource = makeResourceItemElement({
    id: 1,
    name: 'John Doe',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  expect(screen.getByText('John Doe')).toBeDefined();
});

test('resource item renders with selection state', () => {
  const mockResource = makeResourceItemElement({
    id: 2,
    name: 'Jane Smith',
  });
  const mockOnSelect = vi.fn();

  const { rerender } = render(
    <ResourceItem
      resource={mockResource}
      onSelect={mockOnSelect}
      isSelected={false}
    />
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
    <ResourceItem
      resource={mockResource}
      onSelect={mockOnSelect}
      isSelected={true}
    />
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
  const mockResource = makeResourceItemElement({
    id: 3,
    name: 'Bob Johnson',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  const container = screen.getByText('Bob Johnson').closest('div');
  if (container) {
    fireEvent.click(container);
  }

  expect(mockOnSelect).toHaveBeenCalledTimes(1);
});

test('resource item displays driver name and ID', () => {
  const mockResource = makeResourceItemElement({
    id: 3,
    name: 'Charlie Brown',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  expect(screen.getByText('Charlie Brown')).toBeDefined();
});

test('resource item displays battery status indicator', () => {
  const mockResource = makeResourceItemElement({
    batteryCount: 2,
  });
  const mockOnSelect = vi.fn();
  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);
  expect(screen.getByText('2')).toBeDefined();
});

test('resource item handles dragOver event correctly', () => {
  const mockResource = makeResourceItemElement({
    id: 4,
    name: 'Drag Test Driver',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  const container = screen
    .getByText('Drag Test Driver')
    .closest('[data-slot="item"]') as HTMLElement;

  const dragOverEvent = new DragEvent('dragover', {
    bubbles: true,
    cancelable: true,
    dataTransfer: new DataTransfer(),
  });

  fireEvent(container, dragOverEvent);
  expect(dragOverEvent.defaultPrevented).toBe(true);
});

test('resource item handles drop event and stops propagation (#583)', () => {
  const mockResource = makeResourceItemElement({
    id: 5,
    name: 'Drop Test Driver',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  const container = screen
    .getByText('Drop Test Driver')
    .closest('[data-slot="item"]') as HTMLElement;

  const dataTransfer = new DataTransfer();
  dataTransfer.setData('taskId', '123');

  const dropEvent = new DragEvent('drop', {
    bubbles: true,
    cancelable: true,
    dataTransfer,
  });

  const stopPropagationSpy = vi.spyOn(dropEvent, 'stopPropagation');

  fireEvent(container, dropEvent);

  expect(dropEvent.defaultPrevented).toBe(true);
  expect(stopPropagationSpy).toHaveBeenCalled();
});

test('resource item handles dragEnter and applies hover state', () => {
  const mockResource = makeResourceItemElement({
    id: 6,
    name: 'Hover Test Driver',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  const container = screen
    .getByText('Hover Test Driver')
    .closest('[data-slot="item"]') as HTMLElement;

  const dragEnterEvent = new DragEvent('dragenter', {
    bubbles: true,
    cancelable: true,
  });

  fireEvent(container, dragEnterEvent);

  // After dragEnter, should have yellow hover styling
  expect(container.className).toContain('bg-yellow-50');
  expect(container.className).toContain('ring-yellow-300');
});

test('resource item handles dragLeave with relatedTarget outside element (#583)', () => {
  const mockResource = makeResourceItemElement({
    id: 7,
    name: 'Leave Test Driver',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  const container = screen
    .getByText('Leave Test Driver')
    .closest('[data-slot="item"]') as HTMLElement;

  // First trigger dragEnter to set hover state
  fireEvent(
    container,
    new DragEvent('dragenter', { bubbles: true, cancelable: true })
  );

  expect(container.className).toContain('bg-yellow-50');

  // Then trigger dragLeave with relatedTarget outside the element
  const outsideElement = document.createElement('div');
  const dragLeaveEvent = new DragEvent('dragleave', {
    bubbles: true,
    cancelable: true,
    relatedTarget: outsideElement,
  });

  fireEvent(container, dragLeaveEvent);

  // Hover state should be cleared
  expect(container.className).not.toContain('bg-yellow-50');
  expect(container.className).not.toContain('ring-yellow-300');
});

test('resource item handles dragLeave with null relatedTarget (#583 Safari fix)', () => {
  const mockResource = makeResourceItemElement({
    id: 8,
    name: 'Null Leave Test Driver',
  });

  const mockOnSelect = vi.fn();

  render(<ResourceItem resource={mockResource} onSelect={mockOnSelect} />);

  const container = screen
    .getByText('Null Leave Test Driver')
    .closest('[data-slot="item"]') as HTMLElement;

  // First trigger dragEnter to set hover state
  fireEvent(
    container,
    new DragEvent('dragenter', { bubbles: true, cancelable: true })
  );

  expect(container.className).toContain('bg-yellow-50');

  // Then trigger dragLeave with null relatedTarget (Safari behavior)
  const dragLeaveEvent = new DragEvent('dragleave', {
    bubbles: true,
    cancelable: true,
    relatedTarget: null,
  });

  fireEvent(container, dragLeaveEvent);

  // Hover state should be cleared because relatedTarget is null
  expect(container.className).not.toContain('bg-yellow-50');
  expect(container.className).not.toContain('ring-yellow-300');
});
