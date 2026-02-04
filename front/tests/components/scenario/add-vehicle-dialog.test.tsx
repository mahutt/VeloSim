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
import AddVehicleDialog from '~/components/scenario/add-vehicle-dialog';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    warning: vi.fn(),
  },
}));

describe('AddVehicleDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnSubmit = vi.fn();
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
      <AddVehicleDialog
        scenarioContent={scenarioContent}
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
      screen.getByRole('heading', { name: 'Add Vehicle' })
    ).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <AddVehicleDialog
        scenarioContent={mockScenarioContent}
        open={false}
        onOpenChange={mockOnOpenChange}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows validation errors for empty required fields', async () => {
    setup();

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Vehicle name is required/i)).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid latitude', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);

    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });
    fireEvent.change(latitudeInput, { target: { value: '100' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Latitude must be between -90 and 90/i)
      ).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid longitude', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });
    fireEvent.change(longitudeInput, { target: { value: '-200' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Longitude must be between -180 and 180/i)
      ).toBeInTheDocument();
    });
  });

  it('submits valid data with only required fields', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);

    fireEvent.change(nameInput, { target: { value: 'Vehicle 1' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Vehicle 1',
      });
    });
  });

  it('submits valid data with position', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'Vehicle 1' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5017' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5673' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Vehicle 1',
        latitude: 45.5017,
        longitude: -73.5673,
      });
    });
  });

  it('submits valid data with all fields', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);
    const batteryCountInput = screen.getByLabelText(/Battery Count/i);

    fireEvent.change(nameInput, { target: { value: 'Vehicle 1' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5017' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5673' } });
    fireEvent.change(batteryCountInput, { target: { value: '5' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Vehicle 1',
        latitude: 45.5017,
        longitude: -73.5673,
        batteryCount: 5,
      });
    });
  });

  it('resets form on cancel', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('trims whitespace from vehicle name', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);

    fireEvent.change(nameInput, { target: { value: '  Vehicle 1  ' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Vehicle 1',
        })
      );
    });
  });

  it('validates that latitude requires longitude and vice versa', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);

    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Longitude is required when latitude is provided/i)
      ).toBeInTheDocument();
    });
  });

  it('shows error when no drivers available for vehicle with position', async () => {
    const scenarioContentNoDrivers = JSON.stringify({
      drivers: [],
      vehicles: [],
      stations: [],
    });

    setup(scenarioContentNoDrivers);

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      const errorMessages = screen.getAllByText(
        /Insufficient drivers for positioned vehicle/i
      );
      expect(errorMessages.length).toBeGreaterThan(0);
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows error when all drivers are already assigned', async () => {
    const scenarioContentDriversAssigned = JSON.stringify({
      drivers: [{ name: 'Driver 1', shifts: [[0, 3600]] }],
      vehicles: [{ name: 'Vehicle 1', position: [-73.5, 45.5] }],
      stations: [],
    });

    setup(scenarioContentDriversAssigned);

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const latitudeInput = screen.getByLabelText(/Latitude/i);
    const longitudeInput = screen.getByLabelText(/Longitude/i);

    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });
    fireEvent.change(latitudeInput, { target: { value: '45.5' } });
    fireEvent.change(longitudeInput, { target: { value: '-73.5' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      const errorMessages = screen.getAllByText(
        /Insufficient drivers for positioned vehicle/i
      );
      expect(errorMessages.length).toBeGreaterThan(0);
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits successfully with battery count', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    const batteryCountInput = screen.getByLabelText(/Battery Count/i);

    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });
    fireEvent.change(batteryCountInput, { target: { value: '3' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Vehicle',
        batteryCount: 3,
      });
    });
  });

  it('closes dialog on successful submit', async () => {
    setup();

    const nameInput = screen.getByLabelText(/Vehicle Name/i);
    fireEvent.change(nameInput, { target: { value: 'Test Vehicle' } });

    const submitButton = screen.getByRole('button', { name: /Add Vehicle/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });
});
