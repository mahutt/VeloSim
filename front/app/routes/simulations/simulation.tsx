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

import 'mapbox-gl/dist/mapbox-gl.css';
import MapContainer from '~/components/map/map-container';
import SelectedItemBar from '~/components/map/selected-item-bar';
import { MapProvider, useMap } from '~/providers/map-provider';
import {
  SimulationProvider,
  useSimulation,
} from '~/providers/simulation-provider';
import ResourceBar from '~/components/resource/resource-bar';
import { useParams } from 'react-router';
import { Loader2 } from 'lucide-react';
import PlaybackControls from '~/components/map/playback-controls';
import SimulationOptions from '~/components/map/simulation-options';
import SimulationClock from '~/components/map/clock';
import HQWidget from '~/components/simulation/hq-widget';
import Scrubber from '~/components/map/scrubber';
import useFeature from '~/hooks/use-feature';
import usePreferences from '~/hooks/use-preferences';
import { TaskAssignmentBanner } from '~/components/task/task-assignment-banner';
import ReportingWidget from '~/components/simulation/reporting-widget';
import BufferOverlay from '~/components/simulation/buffer-overlay';

export function meta() {
  return [{ title: 'Simulation' }];
}

export default function Simulation() {
  const { sim_id } = useParams<{ sim_id: string }>();

  if (!sim_id) return null; // Should never happen due to routing

  return (
    <MapProvider>
      <MapContainer />
      <MapReadyGate simulationId={sim_id} />
    </MapProvider>
  );
}

function MapReadyGate({ simulationId }: { simulationId: string }) {
  const { mapRef, mapLoaded } = useMap();
  if (!mapLoaded || !mapRef.current) return null;
  return (
    <SimulationProvider simulationId={simulationId} map={mapRef.current}>
      <SimulationContent />
    </SimulationProvider>
  );
}

function SimulationContent() {
  const { state } = useSimulation();
  const { t } = usePreferences();
  const { isLoading, currentDay } = state;
  const showScrubber = useFeature('simulationScrubber');

  if (isLoading) {
    return (
      <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <p className="text-lg text-muted-foreground">{t.common.loading}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <BufferOverlay />
      {/* pb-8 is so that the Mapbox & OSM copyright notices aren't blocked */}
      <div className="pointer-events-none absolute inset-0 px-4 pt-4 pb-8 flex flex-row gap-4">
        {/* mt-6 is to give space to the sidebar toggle, flex-col is required for dynamic selected item bar height */}
        <div className="mt-6 w-72 flex flex-col">
          <SelectedItemBar />
        </div>
        <div className="flex-1 min-w-0 flex flex-col justify-between items-center">
          <div>
            <TaskAssignmentBanner />
          </div>
          {showScrubber && (
            <div className="w-2xl max-w-full z-30">
              <Scrubber />
            </div>
          )}
        </div>
        <div
          className={`${getContainerWidth(currentDay)} flex flex-col justify-between gap-2`}
        >
          <div className="flex flex-col gap-2 min-h-0">
            <div className="w-full flex justify-between gap-2 items-center">
              <SimulationClock />
              <PlaybackControls />
              <SimulationOptions />
            </div>
            <ResourceBar />
            <HQWidget />
          </div>
          <ReportingWidget />
        </div>
      </div>
    </>
  );
}

// Dynamic width based on day digit count
export function getContainerWidth(currentDay: number) {
  if (currentDay >= 100) return 'w-[285px]';
  if (currentDay >= 10) return 'w-[276px]';
  return 'w-[268px]';
}
