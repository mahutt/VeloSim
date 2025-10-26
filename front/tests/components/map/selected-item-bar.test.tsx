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

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useSimulation } from '~/providers/simulation-provider';
import SelectedItemBar from '~/components/map/selected-item-bar';
import { SelectedItemType } from '~/types';

// Mock the useSimulation hook
vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('SelectedItemBar', () => {
  it('should not render when no item is selected', () => {
    vi.mocked(useSimulation).mockReturnValue({
      selectedItem: null,
      clearSelection: vi.fn(),
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      resourcesRef: { current: new Map() },
      resources: [],
      assignTaskToResource: vi.fn(),
    });

    const { container } = render(<SelectedItemBar />);
    expect(container.firstChild).toBeNull();
  });

  it('should render station information when station is selected', () => {
    const mockStation = {
      id: 1,
      name: 'Test Station',
      position: [-73.57776, 45.48944] as [number, number],
      tasks: [],
    };

    vi.mocked(useSimulation).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Station,
        value: mockStation,
      },
      clearSelection: vi.fn(),
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      resourcesRef: { current: new Map() },
      resources: [],
      assignTaskToResource: vi.fn(),
    });

    render(<SelectedItemBar />);

    expect(screen.getByText('Station')).toBeInTheDocument();
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('Test Station')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Position')).toBeInTheDocument();
    expect(screen.getByText('Tasks (0)')).toBeInTheDocument();
  });

  it('should render resource information when resource is selected', () => {
    const mockResource = {
      id: 5,
      position: [-73.58, 45.49] as [number, number],
      taskList: [1, 2, 3],
      route: {
        coordinates: [
          [-73.58, 45.49],
          [-73.57, 45.5],
        ] as [number, number][],
      },
    };

    vi.mocked(useSimulation).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Resource,
        value: mockResource,
      },
      clearSelection: vi.fn(),
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      resourcesRef: { current: new Map() },
      resources: [],
      assignTaskToResource: vi.fn(),
    });

    render(<SelectedItemBar />);

    expect(screen.getByText('Resource')).toBeInTheDocument();
    expect(screen.getByText('#5')).toBeInTheDocument();
    expect(screen.getByText('Position')).toBeInTheDocument();
    expect(screen.getByText('Tasks (3)')).toBeInTheDocument();
    expect(screen.getByText('1, 2, 3')).toBeInTheDocument();
  });

  it('should call clearSelection when close button is clicked', async () => {
    const user = userEvent.setup();
    const clearSelectionMock = vi.fn();

    const mockStation = {
      id: 1,
      name: 'Test Station',
      position: [-73.57776, 45.48944] as [number, number],
      tasks: [],
    };

    vi.mocked(useSimulation).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Station,
        value: mockStation,
      },
      clearSelection: clearSelectionMock,
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      resourcesRef: { current: new Map() },
      resources: [],
      assignTaskToResource: vi.fn(),
    });

    render(<SelectedItemBar />);

    const closeButton = screen.getByRole('button');
    await user.click(closeButton);

    expect(clearSelectionMock).toHaveBeenCalledTimes(1);
  });

  it('should display tasks when station has tasks', () => {
    const mockStation = {
      id: 1,
      name: 'Test Station',
      position: [-73.57776, 45.48944] as [number, number],
      tasks: [
        { stationId: 1, type: 'battery_swap' as const },
        { stationId: 1, type: 'battery_swap' as const },
      ],
    };

    vi.mocked(useSimulation).mockReturnValue({
      selectedItem: {
        type: SelectedItemType.Station,
        value: mockStation,
      },
      clearSelection: vi.fn(),
      selectItem: vi.fn(),
      stationsRef: { current: new Map() },
      resourcesRef: { current: new Map() },
      resources: [],
      assignTaskToResource: vi.fn(),
    });

    render(<SelectedItemBar />);

    expect(screen.getByText('Tasks (2)')).toBeInTheDocument();
    expect(screen.getByText('battery swap, battery swap')).toBeInTheDocument();
  });
});
