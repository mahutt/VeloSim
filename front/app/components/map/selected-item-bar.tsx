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

import { X, MapPin } from 'lucide-react';
import { useSimulation } from '~/providers/simulation-provider';
import {
  DriverState,
  type Position,
  type Route,
  type StationTask,
} from '~/types';
import { ScrollArea } from '~/components/ui/scroll-area';
import { Button } from '../ui/button';
import DriverStateBadge from './driver-state-badge';
import { StationTasks } from './station-tasks';
import { DriverTasks } from './driver-tasks';

export enum SelectedItemType {
  Station = 'station',
  Driver = 'driver',
}

export interface PopulatedStation {
  id: number;
  name: string;
  position: Position;
  tasks: StationTask[];
}

export interface PopulatedDriver {
  id: number;
  name: string;
  position: Position;
  tasks: StationTask[];
  route: Route | null;
  state: DriverState;
  inProgressTask: StationTask | null;
}

export type SelectedItem =
  | { type: SelectedItemType.Station; value: PopulatedStation }
  | { type: SelectedItemType.Driver; value: PopulatedDriver };

export default function SelectedItemBar() {
  const { state, engine } = useSimulation();
  const { selectedItems } = state;

  if (selectedItems.length === 0) return null;

  // Multi-selection (2+ items, currently only stations)
  if (selectedItems.length > 1) {
    const stations = selectedItems
      .filter(
        (item): item is SelectedItem & { type: SelectedItemType.Station } =>
          item.type === SelectedItemType.Station
      )
      .map((item) => item.value);

    const totalTasks = stations.reduce((sum, s) => sum + s.tasks.length, 0);

    return (
      <div className="bg-gray-50 flex flex-col gap-2 rounded-lg border py-4 shadow-sm w-full min-w-0">
        <div className="px-5 flex flex-row justify-between items-start gap-1">
          <div className="flex flex-col min-w-0">
            <span className="text-xl font-bold">
              {stations.length} Stations ({totalTasks} tasks)
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => engine.clearSelection()}
            className="h-7 w-7"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <ScrollArea className="mx-2">
          <div className="max-h-50 px-3 space-y-1">
            {stations.map((station) => (
              <div
                key={station.id}
                className="flex flex-row items-center gap-2 rounded-md py-1.5"
              >
                <MapPin className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="text-sm truncate max-w-40">
                  {station.name}
                </span>
                <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
                  ({station.tasks.length} tasks)
                </span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
    );
  }

  // Single selection
  const selectedItem = selectedItems[0];

  const handleClose = () => {
    engine.clearSelection();
  };

  return (
    <div className="bg-gray-50 flex flex-col gap-2 rounded-lg border py-4 shadow-sm">
      <div className="px-5 flex flex-row justify-between items-start gap-1">
        <div className="flex flex-col">
          <span className="text-xl font-bold">{selectedItem.value.name}</span>
          {selectedItem.type === SelectedItemType.Driver && (
            <div className="flex flex-row gap-2">
              <span className="text-muted-foreground text-sm font-normal">
                Driver #{selectedItem.value.id}
              </span>
              <DriverStateBadge state={selectedItem.value.state} />
            </div>
          )}
          {selectedItem.type === SelectedItemType.Station && (
            <span className="text-muted-foreground text-sm font-normal">
              Station #{selectedItem.value.id}
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleClose}
          className="h-7 w-7"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      {selectedItem.value.tasks.length > 0 ? (
        <ScrollArea className="mx-2">
          <div className="max-h-50 px-3 space-y-1">
            {selectedItem.type === SelectedItemType.Station ? (
              <StationTasks station={selectedItem.value} />
            ) : (
              <DriverTasks driver={selectedItem.value} />
            )}
          </div>
        </ScrollArea>
      ) : (
        <p className="text-sm text-muted-foreground px-5">No tasks</p>
      )}
    </div>
  );
}
