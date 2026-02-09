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
import AddStationDialog from '~/components/scenario/add-station-dialog';
import { MONTREAL_BOUNDS } from '~/constants';

describe('AddStationDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnSubmit = vi.fn();

  const setup = (open = true) => {
    return render(
      <AddStationDialog
        open={open}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
      />
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog when open', () => {
    setup();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText(/Station Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Latitude/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Longitude/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Initial Task Count/i)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    setup(false);
    expect(screen.queryByText('Add Station')).not.toBeInTheDocument();
  });

  it('shows validation errors for empty required fields', async () => {
    setup();

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Station name is required')).toBeInTheDocument();
      expect(
        screen.getByText('Valid latitude is required')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Valid longitude is required')
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid latitude', async () => {
    setup();

    const latitudeInput = screen.getByLabelText(/Latitude/i);
    fireEvent.change(latitudeInput, { target: { value: '100' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          new RegExp(
            `must be between ${MONTREAL_BOUNDS.LAT_MIN} and ${MONTREAL_BOUNDS.LAT_MAX}`,
            'i'
          )
        )
      ).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid longitude', async () => {
    setup();

    const longitudeInput = screen.getByLabelText(/Longitude/i);
    fireEvent.change(longitudeInput, { target: { value: '200' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(
          new RegExp(
            `must be between ${MONTREAL_BOUNDS.LON_MIN} and ${MONTREAL_BOUNDS.LON_MAX}`,
            'i'
          )
        )
      ).toBeInTheDocument();
    });
  });

  it('submits valid data correctly', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);
    const taskCountInput = screen.getByLabelText(/Initial Task Count/i);

    fireEvent.change(nameInput, { target: { value: 'Main Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5017' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5673' } });
    fireEvent.change(taskCountInput, { target: { value: '10' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Main Station',
        latitude: 45.5017,
        longitude: -73.5673,
        initialTaskCount: 10,
      });
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('submits valid data without optional initial task count', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'Test Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Station',
        latitude: 45.5,
        longitude: -73.5,
        initialTaskCount: undefined,
      });
    });
  });

  it('resets form on cancel', async () => {
    setup();

    const nameInput = screen.getByLabelText(
      /Station Name/i
    ) as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it('trims whitespace from station name', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: '  Spaced Station  ' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Spaced Station',
        latitude: 45.5,
        longitude: -73.5,
        initialTaskCount: undefined,
      });
    });
  });

  it('shows validation error for negative initial task count', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);
    const taskCountInput = screen.getByLabelText(
      /Initial Task Count/i
    ) as HTMLInputElement;

    // Remove min attribute to allow negative values in test
    taskCountInput.removeAttribute('min');

    fireEvent.change(nameInput, { target: { value: 'Test Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-74.0' } });
    fireEvent.change(taskCountInput, { target: { value: '-5' } });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Must be a non-negative number/i)
      ).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid scheduledTasks format', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);
    const scheduledTasksInput = screen.getByLabelText(/Scheduled Tasks/i);

    fireEvent.change(nameInput, { target: { value: 'Test Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-74.0' } });
    fireEvent.change(scheduledTasksInput, {
      target: { value: 'invalid format, day1:09:30' },
    });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Invalid format/i)).toBeInTheDocument();
      expect(screen.getByText(/Must be dayN:HH:MM/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits successfully with valid scheduledTasks', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Station Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);
    const scheduledTasksInput = screen.getByLabelText(/Scheduled Tasks/i);

    fireEvent.change(nameInput, { target: { value: 'Test Station' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-74.0' } });
    fireEvent.change(scheduledTasksInput, {
      target: { value: 'day1:09:30, day1:14:00, day2:10:00' },
    });

    const submitButton = screen.getByRole('button', { name: /Add Station/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Station',
        latitude: 45.5,
        longitude: -74.0,
        scheduledTasks: ['day1:09:30', 'day1:14:00', 'day2:10:00'],
      });
    });
  });
});
