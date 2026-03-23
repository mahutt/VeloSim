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
  useState,
  type Dispatch,
  type SetStateAction,
  type ReactNode,
} from 'react';
import { DropdownMenuItem } from '../ui/dropdown-menu';
import { toast } from 'sonner';
import AddStationDialog from './add-station-dialog';
import type { ScenarioContentStation } from '~/types';
import usePreferences from '~/hooks/use-preferences';

interface AddStationButtonProps {
  setScenarioContent: Dispatch<SetStateAction<string>>;
  onEdit: () => void;
  icon?: ReactNode;
}

export default function AddStationButton({
  setScenarioContent,
  onEdit,
  icon,
}: AddStationButtonProps) {
  const { t } = usePreferences();
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleAddStation = (stationData: {
    name: string;
    latitude: number;
    longitude: number;
    initialTaskCount?: number;
    scheduledTasks?: string[];
  }) => {
    onEdit(); // Switch to edit mode

    const newStation: ScenarioContentStation = {
      name: stationData.name,
      position: [stationData.longitude, stationData.latitude],
      scheduled_tasks: stationData.scheduledTasks || [],
      ...(stationData.initialTaskCount !== undefined && {
        initial_task_count: stationData.initialTaskCount,
      }),
    };

    setScenarioContent((prev) => {
      let jsonNew;
      try {
        const jsonPrev = JSON.parse(prev);
        const existingStations = Array.isArray(jsonPrev.stations)
          ? jsonPrev.stations
          : [];

        jsonNew = {
          ...jsonPrev,
          stations: [...existingStations, newStation],
        };
      } catch {
        // If parsing fails, create new scenario with just this station
        jsonNew = {
          stations: [newStation],
        };
      }
      return JSON.stringify(jsonNew, null, 2);
    });

    toast.success(
      `${t.scenario.toast.station} "${stationData.name}" ${t.scenario.toast.addedSuccessfully}`
    );
    setDialogOpen(false);
  };

  return (
    <>
      <DropdownMenuItem
        onSelect={(e) => {
          e.preventDefault();
          setDialogOpen(true);
        }}
      >
        {icon}
        {t.scenario.option.addStation}
      </DropdownMenuItem>
      <AddStationDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={handleAddStation}
      />
    </>
  );
}
