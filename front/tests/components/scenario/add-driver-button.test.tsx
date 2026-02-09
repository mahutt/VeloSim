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
import AddDriverButton from '~/components/scenario/add-driver-button';

// Mock the dialog component to avoid Radix UI portal issues
vi.mock('~/components/scenario/add-driver-dialog', () => ({
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
        <h2>Add Driver</h2>
        <button
          onClick={() =>
            onSubmit({
              name: 'Test Driver',
              shift: {
                start_time: 'day1:08:00',
                end_time: 'day1:17:00',
                lunch_break: 'day1:12:00',
              },
            })
          }
        >
          Add Driver
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

describe('AddDriverButton', () => {
  const mockSetScenarioContent = vi.fn();
  const mockOnEdit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const setup = () => {
    return render(
      <AddDriverButton
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );
  };

  it('opens dialog when clicked', async () => {
    setup();

    const button = screen.getByText('Add Driver');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { name: 'Add Driver' })
      ).toBeInTheDocument();
    });
  });

  it('adds driver to existing scenario content', async () => {
    const existingContent = JSON.stringify({
      stations: [{ name: 'Station 1', position: [-73.5, 45.5] }],
      drivers: [
        {
          name: 'Existing Driver',
          shifts: [['day1:08:00', 'day1:17:00']],
        },
      ],
    });

    setup();

    const button = screen.getByText('Add Driver');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });

    // Get the function passed to setScenarioContent
    const updateFn = mockSetScenarioContent.mock.calls[0][0];
    const result = updateFn(existingContent);
    const parsed = JSON.parse(result);

    expect(parsed.drivers).toHaveLength(2);
    expect(parsed.drivers[1]).toEqual({
      name: 'Test Driver',
      shift: {
        start_time: 'day1:08:00',
        end_time: 'day1:17:00',
        lunch_break: 'day1:12:00',
      },
    });
  });

  it('creates drivers array if it does not exist', async () => {
    const emptyContent = JSON.stringify({
      stations: [],
    });

    setup();

    const button = screen.getByText('Add Driver');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });

    const updateFn = mockSetScenarioContent.mock.calls[0][0];
    const result = updateFn(emptyContent);
    const parsed = JSON.parse(result);

    expect(parsed.drivers).toHaveLength(1);
    expect(parsed.drivers[0]).toEqual({
      name: 'Test Driver',
      shift: {
        start_time: 'day1:08:00',
        end_time: 'day1:17:00',
        lunch_break: 'day1:12:00',
      },
    });
  });

  it('handles malformed JSON gracefully', async () => {
    const malformedContent = 'not valid json';

    setup();

    const button = screen.getByText('Add Driver');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSetScenarioContent).toHaveBeenCalled();
    });

    const updateFn = mockSetScenarioContent.mock.calls[0][0];
    const result = updateFn(malformedContent);
    const parsed = JSON.parse(result);

    // Should create a new scenario with just the driver
    expect(parsed.drivers).toHaveLength(1);
    expect(parsed.drivers[0]).toEqual({
      name: 'Test Driver',
      shift: {
        start_time: 'day1:08:00',
        end_time: 'day1:17:00',
        lunch_break: 'day1:12:00',
      },
    });
  });

  it('calls onEdit when driver is added', async () => {
    setup();

    const button = screen.getByText('Add Driver');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnEdit).toHaveBeenCalled();
    });
  });
});
