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
import type {
  GBFSStationInformationResponse,
  ScenarioContentStation,
} from '~/types';
import {
  GBFS_STATION_INFORMATION_STORAGE_KEY,
  GBFS_STATION_INFORMATION_URL,
} from '~/constants';
import { DropdownMenuItem } from '../ui/dropdown-menu';
import axios from 'axios';
import { toast } from 'sonner';

async function getGbfsStations(): Promise<ScenarioContentStation[]> {
  // Check session storage for cached GBFS station information
  const cached = sessionStorage.getItem(GBFS_STATION_INFORMATION_STORAGE_KEY);
  if (cached) {
    try {
      return JSON.parse(cached) as ScenarioContentStation[];
    } catch {
      // If parsing fails, proceed to fetch fresh data
    }
  }

  const response = await axios.get<GBFSStationInformationResponse>(
    GBFS_STATION_INFORMATION_URL
  );

  const stationInformation: ScenarioContentStation[] =
    response.data.data.stations.map((station) => ({
      name: station.name,
      position: [station.lon, station.lat],
      scheduled_tasks: [],
    }));

  // Cache the fetched station information in session storage
  sessionStorage.setItem(
    GBFS_STATION_INFORMATION_STORAGE_KEY,
    JSON.stringify(stationInformation)
  );

  return stationInformation;
}

interface UseGbfsStationsButtonProps {
  setScenarioContent: Dispatch<SetStateAction<string>>;
  onEdit: () => void;
  icon?: ReactNode;
}

export default function UseGbfsStationsButton({
  setScenarioContent,
  onEdit,
  icon,
}: UseGbfsStationsButtonProps) {
  const [loading, setLoading] = useState(false);
  return (
    <DropdownMenuItem
      disabled={loading}
      onClick={async () => {
        onEdit(); // Switch to edit mode
        setLoading(true);
        let stations;
        try {
          stations = await getGbfsStations();
        } catch {
          setLoading(false);
          toast.error('Failed to fetch GBFS station information');
          return;
        }
        setScenarioContent((prev) => {
          let jsonNew;
          try {
            const jsonPrev = JSON.parse(prev);
            jsonNew = {
              ...jsonPrev,
              stations,
            };
          } catch {
            jsonNew = {
              stations,
            };
          }
          return JSON.stringify(jsonNew, null, 2);
        });
        setLoading(false);
        toast.success('GBFS stations loaded successfully');
      }}
    >
      {icon}
      Use GBFS Stations
    </DropdownMenuItem>
  );
}
