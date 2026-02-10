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

import * as SliderPrimitive from '@radix-ui/react-slider';

import { useState } from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import {
  calculateDayFromSeconds,
  formatSecondsToHHMM,
} from '~/utils/clock-utils';
import { useSimulation } from '~/providers/simulation-provider';
import { SIMULATION_FRAMES_PER_KEY_FRAME } from '~/constants';

export default function Scrubber() {
  const {
    startTime,
    simulationSecondsPassed,
    scrubSimulationSecond,
    scrub,
    commitScrub,
  } = useSimulation();

  const [open, setOpen] = useState(false);

  const handleChange = (value: number[]) => {
    console.log('Slider value changed to: ', value);
    scrub(value[0]);
  };

  const handleCommit = () => {
    console.log('Slider value committed: ', scrubSimulationSecond);
    commitScrub(scrubSimulationSecond);
  };

  return (
    <div className="w-full max-w-2xl p-2 rounded-full bg-background border shadow-sm">
      <SliderPrimitive.Root
        data-slot="slider"
        value={[scrubSimulationSecond]}
        onValueChange={handleChange}
        // We use onLostPointerCapture instead of onValueCommit because
        // onValueCommit doesn't fire when the value hasn't changed
        // by the end of the drag.
        onLostPointerCapture={handleCommit}
        min={0}
        max={simulationSecondsPassed}
        // The backend emits a keyframe on every 20th frame, so we set the step to that to ensure the scrubber snaps to keyframes.
        step={SIMULATION_FRAMES_PER_KEY_FRAME}
        className={
          'z-10 relative flex w-full touch-none items-center select-none data-[disabled]:opacity-50 data-[orientation=vertical]:h-full data-[orientation=vertical]:min-h-44 data-[orientation=vertical]:w-auto data-[orientation=vertical]:flex-col'
        }
      >
        <SliderPrimitive.Track
          data-slot="slider-track"
          className={
            'bg-muted relative grow overflow-hidden rounded-full data-[orientation=horizontal]:h-1.5 data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-1.5'
          }
        >
          <SliderPrimitive.Range
            data-slot="slider-range"
            className={
              'bg-primary absolute data-[orientation=horizontal]:h-full data-[orientation=vertical]:w-full'
            }
          />
        </SliderPrimitive.Track>
        <Tooltip open={open}>
          <TooltipTrigger asChild>
            <SliderPrimitive.Thumb
              onMouseEnter={() => setOpen(true)}
              onMouseLeave={() => setOpen(false)}
              data-slot="slider-thumb"
              className={`border-primary ring-ring/50 block size-4 shrink-0 rounded-full border ${
                scrubSimulationSecond === simulationSecondsPassed
                  ? 'bg-red-400'
                  : 'bg-white'
              } shadow-sm transition-[color,background-color,box-shadow] hover:ring-4 focus-visible:ring-4 focus-visible:outline-hidden disabled:pointer-events-none disabled:opacity-50`}
            />
          </TooltipTrigger>
          <TooltipContent>
            <p>
              Day {calculateDayFromSeconds(scrubSimulationSecond, startTime)} -{' '}
              {formatSecondsToHHMM(scrubSimulationSecond, startTime)}
            </p>
          </TooltipContent>
        </Tooltip>
      </SliderPrimitive.Root>
    </div>
  );
}
