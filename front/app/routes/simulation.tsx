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
import { MapProvider } from '~/providers/map-provider';
import { SimulationProvider } from '~/providers/simulation-provider';
import ResourceBar from '~/components/resource/resource-bar';
import { useNavigate } from 'react-router';
import { Button } from '~/components/ui/button';

export function meta() {
  return [{ title: 'Simulation' }];
}

export default function Simulation() {
  const navigate = useNavigate();
  return (
    <>
      <MapProvider>
        <SimulationProvider>
          <MapContainer />
          <ResourceBar />
          {/* Scenario Editor Button above SelectedItemBar */}
          <div className="absolute left-4 top-1 z-50">
            <Button
              onClick={() => navigate('/scenario-editor')}
              className="bg-red-500"
            >
              Go to Scenario Editor
            </Button>
          </div>
          <SelectedItemBar />
        </SimulationProvider>
      </MapProvider>
    </>
  );
}
