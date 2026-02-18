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

import {
  Car,
  ChevronLeft,
  CircleDashed,
  User2,
  UsersRound,
} from 'lucide-react';
import { useState } from 'react';
import Nested from '~/icons/nested';
import { useSimulation } from '~/providers/simulation-provider';
export interface HQEntitiesState {
  type: 'driver' | 'vehicle';
  count: number; // should be > 0
}

export interface HQWidgetProps {
  entities: HQEntitiesState | null; // null indicates all quiet
  driversAtHQ: HQWidgetDriver[];
  driversPendingShift: HQWidgetDriver[];
}

export default function HQWidget() {
  const { state } = useSimulation();
  const { driversAtHQ, driversPendingShift, entities } = state.HQWidgetState;
  const [open, setOpen] = useState<boolean>(false);
  const drivers = [...driversAtHQ, ...driversPendingShift].sort(
    (a, b) => a.minutesTillShift - b.minutesTillShift
  );
  return (
    <div className="w-full bg-gray-50 border shadow rounded-lg">
      {/* header */}
      <button
        className={`${!entities ? 'text-muted-foreground' : ''} w-full flex flex-row items-center gap-2 hover:bg-gray-100 p-2 rounded-lg`}
        onClick={() => setOpen((prev) => !prev)}
      >
        {!entities ? (
          <>
            <CircleDashed size={20} />
            <p className="flex-1 text-left">All quiet at HQ</p>
          </>
        ) : entities.type === 'driver' ? (
          <>
            <UsersRound size={20} className="text-red-500" />
            <p className="flex-1 text-left">
              {entities.count} driver{entities.count > 1 ? 's' : ''} at HQ
            </p>
          </>
        ) : (
          <>
            <Car size={20} className="text-green-500" />
            <p className="flex-1 text-left">
              {entities.count} vehicle{entities.count > 1 ? 's' : ''} at HQ
            </p>
          </>
        )}
        <ChevronLeft
          size={20}
          className={`transition-transform duration-200 ${open ? '-rotate-90' : 'rotate-0'}`}
        />
      </button>
      {/* body */}
      <div className={`${open ? 'h-32' : 'h-0'} duration-200 overflow-hidden`}>
        <div className="overflow-y-auto h-32">
          {drivers.length === 0 ? (
            <p className="w-full h-full flex items-center justify-center text-muted-foreground text-sm">
              {/* <CircleDashed size={20} /> */}
              No pending shifts
            </p>
          ) : (
            drivers.map((driver) => (
              <HQWidgetDriverRow key={driver.id} driver={driver} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export interface HQWidgetDriver {
  id: number;
  name: string;
  minutesTillShift: number; // a negative value indicates time since shift started
}

function HQWidgetDriverRow({ driver }: { driver: HQWidgetDriver }) {
  const hours = Math.floor(Math.abs(driver.minutesTillShift) / 60);
  const minutes = Math.abs(driver.minutesTillShift) % 60;
  const formattedTime = `${driver.minutesTillShift < 0 ? '-' : ''}${hours}:${minutes
    .toString()
    .padStart(2, '0')}`;

  return (
    <div className="flex flex-row items-center gap-1 px-3 py-1">
      <Nested />
      <User2 size={18} />
      <p className="flex-1 truncate">{driver.name}</p>
      <p
        className={
          driver.minutesTillShift <= 0 ? 'text-red-500' : 'text-green-600'
        }
      >
        {formattedTime}
      </p>
    </div>
  );
}
