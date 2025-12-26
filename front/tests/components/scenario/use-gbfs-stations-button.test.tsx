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
import UseGbfsStationsButton from '~/components/scenario/use-gbfs-stations-button';
import { toast } from 'sonner';
import axios from 'axios';

// Mock dependencies
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
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
      onClick,
    }: {
      children: React.ReactNode;
      onClick: () => void;
    }) => <div onClick={onClick}>{children}</div>,
  };
});

vi.mock('axios');

describe('UseGbfsStationsButton', () => {
  const mockSetScenarioContent = vi.fn();
  const mockOnEdit = vi.fn();

  const mockStations = {
    data: {
      data: {
        stations: [
          { name: 'Station 1', lon: -73.5, lat: 45.5 },
          { name: 'Station 2', lon: -73.6, lat: 45.6 },
        ],
      },
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('makes successful request to endpoint and calls toast.success', async () => {
    vi.mocked(axios.get).mockResolvedValue(mockStations);

    render(
      <UseGbfsStationsButton
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );

    const button = screen.getByText('Use GBFS Stations');
    fireEvent.click(button);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'GBFS stations loaded successfully'
      );
    });

    expect(mockOnEdit).toHaveBeenCalled();
    expect(mockSetScenarioContent).toHaveBeenCalled();
  });

  it('makes failed request to endpoint and calls toast.error', async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error('Network error'));

    render(
      <UseGbfsStationsButton
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );

    const button = screen.getByText('Use GBFS Stations');
    fireEvent.click(button);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Failed to fetch GBFS station information'
      );
    });

    expect(mockOnEdit).toHaveBeenCalled();
    expect(mockSetScenarioContent).not.toHaveBeenCalled();
  });

  it('fetches from cache when sessionStorage is set with valid JSON and does not make endpoint call', async () => {
    const cachedStations = [
      {
        name: 'Cached Station 1',
        position: [-73.5, 45.5],
        scheduled_tasks: [],
      },
      {
        name: 'Cached Station 2',
        position: [-73.6, 45.6],
        scheduled_tasks: [],
      },
    ];

    sessionStorage.setItem(
      'gbfs_station_information',
      JSON.stringify(cachedStations)
    );

    render(
      <UseGbfsStationsButton
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );

    const button = screen.getByText('Use GBFS Stations');
    fireEvent.click(button);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'GBFS stations loaded successfully'
      );
    });

    expect(axios.get).not.toHaveBeenCalled();
    expect(mockOnEdit).toHaveBeenCalled();
    expect(mockSetScenarioContent).toHaveBeenCalled();
  });

  it('fetches from cache when sessionStorage is set, then makes endpoint call due to invalid JSON parse', async () => {
    // Set invalid JSON in sessionStorage
    sessionStorage.setItem('gbfs_station_information', 'invalid json');

    vi.mocked(axios.get).mockResolvedValue(mockStations);

    render(
      <UseGbfsStationsButton
        setScenarioContent={mockSetScenarioContent}
        onEdit={mockOnEdit}
      />
    );

    const button = screen.getByText('Use GBFS Stations');
    fireEvent.click(button);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith(
        'GBFS stations loaded successfully'
      );
    });

    expect(mockOnEdit).toHaveBeenCalled();
    expect(mockSetScenarioContent).toHaveBeenCalled();
  });
});
