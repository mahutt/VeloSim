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

import { describe, it, expect, vi, type Mock } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlaybackControls from '~/components/map/playback-controls';
import {
  useSimulation,
  type SimulationContextType,
} from '~/providers/simulation-provider';
import type SimulationEngine from '~/lib/simulation-engine';

vi.mock('~/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

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

describe('PlaybackControls', () => {
  it('renders playback controls with initial speed', () => {
    render(<PlaybackControls />);
    expect(screen.getByText('1x')).toBeInTheDocument();
  });

  it('renders with play button when initially paused', () => {
    useSimulation().state.paused = true;
    render(<PlaybackControls />);

    const playButton = screen.getByRole('button', { name: 'Play simulation' });
    expect(playButton.querySelector('svg')).toBeInTheDocument();
  });

  it('renders with pause button when initially playing', () => {
    useSimulation().state.paused = false;
    render(<PlaybackControls />);

    const pauseButton = screen.getByRole('button', {
      name: 'Pause simulation',
    });
    expect(pauseButton.querySelector('svg')).toBeInTheDocument();
  });

  it('opens speed dropdown menu when speed button is clicked', async () => {
    render(<PlaybackControls />);
    const speedButton = screen.getByText('1x');
    // Click the button to open the dropdown
    await userEvent.click(speedButton);

    await waitFor(() => {
      expect(screen.getByRole('menu')).toBeInTheDocument();
    });

    // Now check for the menu items within the menu
    const menu = screen.getByRole('menu');
    expect(within(menu).getByText('0.5x')).toBeInTheDocument();
    expect(within(menu).getByText('1x')).toBeInTheDocument();
    expect(within(menu).getByText('2x')).toBeInTheDocument();
    expect(within(menu).getByText('4x')).toBeInTheDocument();
    expect(within(menu).getByText('8x')).toBeInTheDocument();
  });

  it('does not show speed 0 in dropdown menu', async () => {
    render(<PlaybackControls />);
    const speedButton = screen.getByText('1x');

    await userEvent.click(speedButton);

    await waitFor(() => {
      expect(screen.getByRole('menu')).toBeInTheDocument();
    });
    const menu = screen.getByRole('menu');
    expect(within(menu).queryByText('0x')).not.toBeInTheDocument();
  });

  it('handles successful speed change when playing', async () => {
    render(<PlaybackControls />);
    // (api.post as Mock).mockResolvedValueOnce({ data: {} });

    const speedButton = screen.getByText('1x');
    await userEvent.click(speedButton);

    const speed2x = await screen.findByText('2x');
    await userEvent.click(speed2x);

    expect(mockUseSimulation().engine.setSpeed).toHaveBeenCalledWith(2);
  });

  it('handles successful pause toggle', async () => {
    useSimulation().state.paused = false;
    render(<PlaybackControls />);
    const pauseButton = screen.getByTestId('simulation-pause-play-button');
    await userEvent.click(pauseButton);
    expect(mockUseSimulation().engine.setPaused).toHaveBeenCalledWith(true);
  });

  it('handles successful play toggle', async () => {
    mockUseSimulation().state.paused = true;
    render(<PlaybackControls />);
    const pauseButton = screen.getByTestId('simulation-pause-play-button');
    await userEvent.click(pauseButton);
    expect(mockUseSimulation().engine.setPaused).toHaveBeenCalledWith(false);
  });

  it('disables controls while speed update is in progress', async () => {
    render(<PlaybackControls />);
    let resolveSetSpeed: (value: { data: null }) => void;
    const setSpeedPromise = new Promise((resolve) => {
      resolveSetSpeed = resolve;
    });
    (mockUseSimulation().engine.setSpeed as Mock).mockReturnValueOnce(
      setSpeedPromise
    );

    const speedButton = screen.getByText('1x');
    await userEvent.click(speedButton);

    const speed2x = await screen.findByText('2x');
    await userEvent.click(speed2x);
    await userEvent.click(speedButton);

    // Controls should be disabled while loading
    await waitFor(() => {
      const dropdownMenu = screen.getByRole('menu');
      expect(dropdownMenu).toHaveAttribute('aria-disabled', 'true');
    });

    resolveSetSpeed!({ data: null });

    await waitFor(() => {
      const dropdownMenu = screen.getByRole('menu');
      expect(dropdownMenu).toHaveAttribute('aria-disabled', 'false');
    });
  });
});
