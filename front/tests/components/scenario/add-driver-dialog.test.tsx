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
import AddDriverDialog from '~/components/scenario/add-driver-dialog';

describe('AddDriverDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const setup = () => {
    return render(
      <AddDriverDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
      />
    );
  };

  it('renders dialog when open', () => {
    setup();

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Add Driver' })
    ).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <AddDriverDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows validation errors for empty required fields', async () => {
    setup();

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Driver name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Start time is required/i)).toBeInTheDocument();
      expect(screen.getByText(/End time is required/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid start time format', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'invalid' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Invalid format. Use dayN:HH:MM/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid end time format', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: '17:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Invalid format. Use dayN:HH:MM/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid lunch break format', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);
    const lunchBreakInput = screen.getByLabelText(/Lunch Break/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });
    fireEvent.change(lunchBreakInput, { target: { value: '12:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Invalid format. Use dayN:HH:MM/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits valid data with only required fields', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Driver',
        shift: {
          start_time: 'day1:08:00',
          end_time: 'day1:17:00',
        },
      });
    });
  });

  it('submits valid data with lunch break', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);
    const lunchBreakInput = screen.getByLabelText(/Lunch Break/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });
    fireEvent.change(lunchBreakInput, { target: { value: 'day1:12:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Driver',
        shift: {
          start_time: 'day1:08:00',
          end_time: 'day1:17:00',
          lunch_break: 'day1:12:00',
        },
      });
    });
  });

  it('resets form on cancel', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('trims whitespace from driver name', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: '  Test Driver  ' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Driver',
        shift: {
          start_time: 'day1:08:00',
          end_time: 'day1:17:00',
        },
      });
    });
  });

  it('trims whitespace from time fields', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: '  day1:08:00  ' } });
    fireEvent.change(endTimeInput, { target: { value: '  day1:17:00  ' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Driver',
        shift: {
          start_time: 'day1:08:00',
          end_time: 'day1:17:00',
        },
      });
    });
  });

  it('accepts multi-digit day numbers', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day10:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day10:17:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Driver',
        shift: {
          start_time: 'day10:08:00',
          end_time: 'day10:17:00',
        },
      });
    });
  });

  it('shows error when end time is before start time', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:17:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:08:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/End time must be after start time/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows error when lunch break is before start time', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);
    const lunchBreakInput = screen.getByLabelText(/Lunch Break/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });
    fireEvent.change(lunchBreakInput, { target: { value: 'day1:07:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Lunch break must be between start and end time/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows error when lunch break is after end time', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Driver Name/i);
    const startTimeInput = screen.getByLabelText(/Shift Start Time/i);
    const endTimeInput = screen.getByLabelText(/Shift End Time/i);
    const lunchBreakInput = screen.getByLabelText(/Lunch Break/i);

    fireEvent.change(nameInput, { target: { value: 'Test Driver' } });
    fireEvent.change(startTimeInput, { target: { value: 'day1:08:00' } });
    fireEvent.change(endTimeInput, { target: { value: 'day1:17:00' } });
    fireEvent.change(lunchBreakInput, { target: { value: 'day1:18:00' } });

    const submitButton = screen.getByRole('button', { name: /Add Driver/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Lunch break must be between start and end time/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
});
