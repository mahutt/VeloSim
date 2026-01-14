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

import { Pause, Play } from 'lucide-react';
import { Separator } from '~/components/ui/separator';
import { useState } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu';
import {
  SPEED_OPTIONS,
  useSimulation,
  type Speed,
} from '~/providers/simulation-provider';
import api from '~/api';
import useError from '~/hooks/use-error';

type NonZeroSpeed = Exclude<Speed, 0>;

export default function PlaybackControls() {
  const { displayError } = useError();
  const { speedRef, simId } = useSimulation();
  const [speed, setSpeed] = useState<NonZeroSpeed>(
    speedRef.current === 0 ? 1 : speedRef.current
  );
  const [paused, setPaused] = useState<boolean>(speedRef.current === 0);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSpeedChange = async (newSpeed: NonZeroSpeed) => {
    const previousSpeed = speed;
    setSpeed(newSpeed); // Optimistic UI update

    // If the simulation is paused, do not send speed update to server
    if (paused) return;

    setLoading(true); // Block speed changes while updating speed

    try {
      await api.post(`/simulation/${simId!}/playbackSpeed`, {
        playback_speed: newSpeed,
      });
    } catch (error) {
      console.error('Failed to update speed:', error);
      displayError(
        'Speed Update Error',
        'Failed to update speed. Please try again.'
      );
      setSpeed(previousSpeed); // Revert to previous speed on error
      setLoading(false);
      return;
    }

    setLoading(false);
    speedRef.current = newSpeed;
  };

  const handlePausePlayToggle = async () => {
    const previousPaused = paused;
    setPaused(!paused); // Optimistic UI update
    setLoading(true); // Block speed changes while updating speed

    try {
      await api.post(`/simulation/${simId!}/playbackSpeed`, {
        // If resuming, use the last speed; if pausing, set speed to 0
        playback_speed: previousPaused ? speed : 0,
      });
    } catch (error) {
      console.error('Failed to toggle pause / play simulation:', error);
      displayError(
        'Playback Toggle Error',
        'Failed to toggle pause / play simulation. Please try again.'
      );
      setPaused(previousPaused); // Revert to previous paused state on error
      setLoading(false);
      return;
    }

    setLoading(false);
    speedRef.current = previousPaused ? speed : 0;
  };

  if (!simId) return null;

  return (
    <div className="bg-background border rounded-md shadow-sm overflow-hidden h-10">
      <div
        className="grid h-full"
        style={{ gridTemplateColumns: '1fr 1px 1fr' }}
      >
        <div className="px-2 flex items-center justify-center">
          <DropdownMenu>
            <DropdownMenuTrigger className="cursor-pointer" asChild>
              <button className="select-none text-center text-sm w-7 hover:text-foreground/80">
                {speed}x
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="bg-background"
              aria-disabled={loading}
            >
              {SPEED_OPTIONS.filter((option) => option !== 0).map((option) => (
                <DropdownMenuItem
                  key={option}
                  onSelect={() => handleSpeedChange(option)}
                  className="flex justify-center items-center"
                  disabled={loading}
                >
                  {option}x
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center">
          <Separator orientation="vertical" className="h-6" />
        </div>
        <button
          className="group px-2 flex items-center justify-center disabled:opacity-50 disabled:pointer-events-none hover:bg-accent"
          onClick={handlePausePlayToggle}
          disabled={loading}
          aria-label={paused ? 'Play simulation' : 'Pause simulation'}
          data-testid="simulation-pause-play-button"
        >
          {paused ? (
            <Play
              className="group-active:scale-90 h-4 w-4"
              fill="currentColor"
              strokeWidth={0}
            />
          ) : (
            <Pause
              className="group-active:scale-90 h-4 w-4"
              fill="currentColor"
              strokeWidth={0}
            />
          )}
        </button>
      </div>
    </div>
  );
}
