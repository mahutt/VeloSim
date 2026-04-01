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
import { SPEED_OPTIONS, useSimulation } from '~/providers/simulation-provider';

export default function PlaybackControls() {
  const { state, engine } = useSimulation();
  const { nonZeroSpeed, paused } = state;
  const [loading, setLoading] = useState<boolean>(false);

  return (
    <div className="pointer-events-auto bg-background border rounded-md shadow-sm overflow-hidden h-10">
      <div
        className="grid h-full"
        style={{ gridTemplateColumns: '1fr 1px 1fr' }}
      >
        <div className="px-1 flex items-center justify-center">
          <DropdownMenu>
            <DropdownMenuTrigger className="cursor-pointer" asChild>
              <button className="select-none text-center text-sm w-7 hover:text-foreground/80">
                {nonZeroSpeed}x
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="bg-background"
              aria-disabled={loading}
            >
              {SPEED_OPTIONS.filter((option) => option !== 0).map((option) => (
                <DropdownMenuItem
                  key={option}
                  onSelect={async () => {
                    setLoading(true);
                    await engine.setSpeed(option);
                    setLoading(false);
                  }}
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
          className="group px-1 flex items-center justify-center disabled:opacity-50 disabled:pointer-events-none hover:bg-accent"
          onClick={async () => {
            setLoading(true);
            await engine.setPaused(!paused);
            setLoading(false);
          }}
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
