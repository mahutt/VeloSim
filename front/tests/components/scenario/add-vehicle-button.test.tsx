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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AddVehicleButton from '~/components/scenario/add-vehicle-button';

// Mock the dialog component to avoid Radix UI portal issues
vi.mock('~/components/scenario/add-vehicle-dialog', () => ({
  default: ({
    open,
    onSubmit,
  }: {
    open: boolean;
    onSubmit: (data: unknown) => void;
  }) => {
    if (!open) return null;
    return (
      <div role="dialog">
        <h2>Add Vehicle</h2>
        <button
          onClick={() =>
            onSubmit({
              name: 'Test Vehicle',
              latitude: 45.5,
              longitude: -73.5,
              batteryCount: 3,
            })
          }
        >
          Add Vehicle
        </button>
      </div>
    );
  },
}));

// Mock the DropdownMenuItem
vi.mock('~/components/ui/dropdown-menu', () => ({
  DropdownMenuItem: ({
    children,
    onSelect,
  }: {
    children: React.ReactNode;
    onSelect: (e: Event) => void;
  }) => (
    <div
      onClick={() => {
        const mockEvent = { preventDefault: () => {} } as Event;
        onSelect(mockEvent);
      }}
    >
      {children}
    </div>
  ),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    warning: vi.fn(),
  },
}));

describe('AddVehicleButton', () => {
  const mockSetScenarioContent = vi.fn();
  const mockOnEdit = vi.fn();
  const mockScenarioContent = JSON.stringify({
    drivers: [
      { name: 'Driver 1', shifts: [[0, 3600]] },
      { name: 'Driver 2', shifts: [[0, 3600]] },
    ],
    vehicles: [],
    stations: [],
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const setup = (scenarioContent = mockScenarioContent) => {
    return render(
      <AddVehicleButton
        scenarioContent={scenarioContent}
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );
  };

  it('opens dialog when clicked', async () => {
    setup();

    const button = screen.getByText('Add Vehicle');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { name: 'Add Vehicle' })
      ).toBeInTheDocument();
    });
  });

  it('adds vehicle to existing scenario content', async () => {
    const existingContent = JSON.stringify({
      stations: [{ name: 'Station 1', position: [-73.5, 45.5] }],
      vehicles: [{ name: 'Existing Vehicle', battery_count: 3 }],
    });

    setup();

    const button = screen.getByText('Add Vehicle');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });

    // Get the function passed to setScenarioContent
    const updateFn = mockSetScenarioContent.mock.calls[0][0];
    const result = updateFn(existingContent);
    const parsed = JSON.parse(result);

    expect(parsed.vehicles).toHaveLength(2);
    expect(parsed.vehicles[1]).toEqual({
      name: 'Test Vehicle',
      position: [-73.5, 45.5],
      battery_count: 3,
    });
  });

  it('creates new scenario content when parsing fails', async () => {
    setup();

    const button = screen.getByText('Add Vehicle');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });

    const updateFn = mockSetScenarioContent.mock.calls[0][0];
    const result = updateFn('invalid json');
    const parsed = JSON.parse(result);

    expect(parsed.vehicles).toHaveLength(1);
    expect(parsed.vehicles[0].name).toBe('Test Vehicle');
  });

  it('handles empty vehicles array in existing content', async () => {
    const existingContent = JSON.stringify({
      stations: [],
    });

    setup();

    const button = screen.getByText('Add Vehicle');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });

    const updateFn = mockSetScenarioContent.mock.calls[0][0];
    const result = updateFn(existingContent);
    const parsed = JSON.parse(result);

    expect(parsed.vehicles).toHaveLength(1);
    expect(parsed.vehicles[0].name).toBe('Test Vehicle');
  });

  it('calls onEdit when adding vehicle', async () => {
    setup();

    const button = screen.getByText('Add Vehicle');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnEdit).toHaveBeenCalled();
    });
  });
});
