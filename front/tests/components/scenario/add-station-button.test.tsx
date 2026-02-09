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

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AddStationButton from '~/components/scenario/add-station-button';
import { toast } from 'sonner';

// Mock dependencies
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    warning: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('~/components/ui/dropdown-menu', async (importActual) => {
  const actual =
    await importActual<typeof import('~/components/ui/dropdown-menu')>();
  return {
    ...actual,
    DropdownMenuItem: ({
      children,
      onSelect,
    }: {
      children: React.ReactNode;
      onSelect: (e: Event) => void;
    }) => (
      <div
        onClick={() => {
          const event = new Event('select');
          Object.defineProperty(event, 'preventDefault', {
            value: vi.fn(),
          });
          onSelect(event);
        }}
      >
        {children}
      </div>
    ),
  };
});

describe('AddStationButton', () => {
  const mockSetScenarioContent = vi.fn();
  const mockOnEdit = vi.fn();

  const setup = () => {
    return render(
      <AddStationButton
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the Add Station button', () => {
    setup();
    expect(screen.getByText('Add Station')).toBeInTheDocument();
  });

  it('opens dialog when clicked', async () => {
    setup();

    const button = screen.getByText('Add Station');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { name: 'Add Station' })
      ).toBeInTheDocument();
    });
  });

  it('adds station to existing scenario content', async () => {
    const existingContent = JSON.stringify(
      {
        stations: [
          {
            name: 'Existing Station',
            position: [-73.5, 45.5],
            scheduled_tasks: [],
          },
        ],
      },
      null,
      2
    );

    mockSetScenarioContent.mockImplementation((updater) => {
      const result =
        typeof updater === 'function' ? updater(existingContent) : updater;
      const parsed = JSON.parse(result);
      expect(parsed.stations).toHaveLength(2);
      expect(parsed.stations[1].name).toBe('New Station');
      expect(parsed.stations[1].position).toEqual([-73.6, 45.6]);
    });

    setup();

    const button = screen.getByText('Add Station');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    // Fill in the form
    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'New Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.6' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.6' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnEdit).toHaveBeenCalled();
      expect(mockSetScenarioContent).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith(
        'Station "New Station" added successfully'
      );
    });
  });

  it('creates new scenario content when parsing fails', async () => {
    const invalidContent = 'invalid json';

    mockSetScenarioContent.mockImplementation((updater) => {
      const result =
        typeof updater === 'function' ? updater(invalidContent) : updater;
      const parsed = JSON.parse(result);
      expect(parsed.stations).toHaveLength(1);
      expect(parsed.stations[0].name).toBe('First Station');
    });

    setup();

    const button = screen.getByText('Add Station');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'First Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });
  });

  it('adds station with initial task count', async () => {
    const existingContent = JSON.stringify({ stations: [] }, null, 2);

    mockSetScenarioContent.mockImplementation((updater) => {
      const result =
        typeof updater === 'function' ? updater(existingContent) : updater;
      const parsed = JSON.parse(result);
      expect(parsed.stations[0].initial_task_count).toBe(5);
    });

    setup();

    const button = screen.getByText('Add Station');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);
    const taskCountInput = screen.getByLabelText(/Initial Task Count/i);

    fireEvent.change(nameInput, { target: { value: 'Task Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });
    fireEvent.change(taskCountInput, { target: { value: '5' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });
  });

  it('handles empty stations array in existing content', async () => {
    const existingContent = JSON.stringify(
      {
        other_field: 'value',
      },
      null,
      2
    );

    mockSetScenarioContent.mockImplementation((updater) => {
      const result =
        typeof updater === 'function' ? updater(existingContent) : updater;
      const parsed = JSON.parse(result);
      expect(parsed.stations).toHaveLength(1);
      expect(parsed.other_field).toBe('value');
    });

    setup();

    const button = screen.getByText('Add Station');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'New Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });
  });
});
