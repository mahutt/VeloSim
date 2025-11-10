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

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlaybackControls from '~/components/map/playback-controls';
import { useSimulation } from '~/providers/simulation-provider';
import api from '~/api';
import { mockDisplayError } from 'tests/mocks';

vi.mock('~/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

vi.mock(import('~/providers/simulation-provider'), async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useSimulation: vi.fn(),
  };
});

describe('PlaybackControls', () => {
  const mockSpeedRef = { current: 1 };
  const mockSimId = 123;

  beforeEach(() => {
    vi.clearAllMocks();
    mockSpeedRef.current = 1;
    (useSimulation as Mock).mockReturnValue({
      speedRef: mockSpeedRef,
      simId: mockSimId,
    });
  });

  it('does not render when simId is null', () => {
    (useSimulation as Mock).mockReturnValue({
      speedRef: mockSpeedRef,
      simId: null,
    });

    const { container } = render(<PlaybackControls />);
    expect(container.firstChild).toBeNull();
  });

  it('renders playback controls with initial speed', () => {
    render(<PlaybackControls />);
    expect(screen.getByText('1x')).toBeInTheDocument();
  });

  it('renders with play button when initially paused', () => {
    mockSpeedRef.current = 0;
    render(<PlaybackControls />);

    const playButton = screen.getByRole('button', { name: 'Play simulation' });
    expect(playButton.querySelector('svg')).toBeInTheDocument();
  });

  it('renders with pause button when initially playing', () => {
    mockSpeedRef.current = 1;
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
    (api.post as Mock).mockResolvedValueOnce({ data: {} });

    const speedButton = screen.getByText('1x');
    await userEvent.click(speedButton);

    const speed2x = await screen.findByText('2x');
    await userEvent.click(speed2x);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        `/simulation/${mockSimId}/playbackSpeed`,
        {
          playback_speed: 2,
        }
      );
      expect(mockSpeedRef.current).toBe(2);
    });
  });

  it('updates speed locally but does not call API when paused', async () => {
    mockSpeedRef.current = 0;
    render(<PlaybackControls />);

    const speedButton = screen.getByText('1x');
    await userEvent.click(speedButton);

    const speed2x = await screen.findByText('2x');
    await userEvent.click(speed2x);

    await waitFor(() => {
      expect(screen.getByText('2x')).toBeInTheDocument();
    });

    expect(api.post).not.toHaveBeenCalled();
  });

  it('handles speed change error and reverts to previous speed', async () => {
    render(<PlaybackControls />);
    (api.post as Mock).mockRejectedValueOnce(new Error('API Error'));

    const speedButton = screen.getByText('1x');
    await userEvent.click(speedButton);

    const speed2x = await screen.findByText('2x');
    await userEvent.click(speed2x);

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Speed Update Error',
        'Failed to update speed. Please try again.'
      );
      expect(screen.getByText('1x')).toBeInTheDocument();
    });
  });

  it('handles successful pause toggle', async () => {
    render(<PlaybackControls />);
    (api.post as Mock).mockResolvedValueOnce({ data: {} });

    const pauseButton = screen.getByTestId('simulation-pause-play-button');
    await userEvent.click(pauseButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        `/simulation/${mockSimId}/playbackSpeed`,
        {
          playback_speed: 0,
        }
      );
    });
  });

  it('handles successful play toggle', async () => {
    mockSpeedRef.current = 0;
    render(<PlaybackControls />);
    (api.post as Mock).mockResolvedValueOnce({ data: {} });

    const pauseButton = screen.getByTestId('simulation-pause-play-button');
    await userEvent.click(pauseButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        `/simulation/${mockSimId}/playbackSpeed`,
        {
          playback_speed: 1,
        }
      );
    });
  });

  it('handles pause/play toggle error and reverts state', async () => {
    render(<PlaybackControls />);
    (api.post as Mock).mockRejectedValueOnce(new Error('API Error'));

    const pauseButton = screen.getByTestId('simulation-pause-play-button');
    await userEvent.click(pauseButton);

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Playback Toggle Error',
        'Failed to toggle pause / play simulation. Please try again.'
      );
    });
  });

  it('disables controls while speed update is in progress', async () => {
    render(<PlaybackControls />);
    let resolvePost: (value: { data: null }) => void;
    const postPromise = new Promise((resolve) => {
      resolvePost = resolve;
    });
    (api.post as Mock).mockReturnValueOnce(postPromise);

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

    resolvePost!({ data: null });

    await waitFor(() => {
      const dropdownMenu = screen.getByRole('menu');
      expect(dropdownMenu).toHaveAttribute('aria-disabled', 'false');
    });
  });
});
