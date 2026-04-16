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

  return (
    <>
      {isLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <p className="text-lg text-muted-foreground">{t.common.loading}</p>
          </div>
        </div>
      )}
      {!isLoading && (
        <>
          <BufferOverlay />
          <TaskAssignmentBanner />
          <div className="absolute top-12 left-4 z-10 w-72">
            <SelectedItemBar />
          </div>
          {/* max-h-[calc(100vh-2.5rem) is set so that the Mapbox & OSM copyright notices aren't blocked. */}
          <div
            className={`${getContainerWidth(currentDay)} pointer-events-none absolute top-4 right-4 flex flex-col justify-between gap-2 h-[calc(100vh-2.5rem)]`}
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
          {showScrubber && (
            <div className="z-60 absolute bottom-10 left-1/2 -translate-x-1/2 w-2xl max-w-full px-2">
              <Scrubber />
            </div>
          )}
        </>
      )}
    </>
  );
}

// Dynamic width based on day digit count
export function getContainerWidth(currentDay: number) {
  if (currentDay >= 100) return 'w-[285px]';
  if (currentDay >= 10) return 'w-[276px]';
  return 'w-[268px]';
}
