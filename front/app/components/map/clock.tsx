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

import { Clock as ClockIcon } from 'lucide-react';
import { useSimulation } from '~/providers/simulation-provider';

export default function Clock() {
  const { formattedSimTime, currentDay } = useSimulation();

  // HH:MM time format
  const time = formattedSimTime ?? '--:--';

  return (
    <div className="bg-gray-50 border shadow rounded-md">
      <div className="px-2 py-1 flex items-center gap-2 font-mono">
        <ClockIcon className="h-4 w-4 text-gray-600" />
        <div className="flex items-center gap-1">
          <span className="text-sm font-medium text-gray-700">
            Day {currentDay}
          </span>
          <span className="text-gray-400">—</span>
          <span className="text-sm font-medium text-gray-900">{time}</span>
        </div>
      </div>
    </div>
  );
}
