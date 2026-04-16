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

import { Menu } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { useSimulation } from '~/providers/simulation-provider';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '~/components/ui/dropdown-menu';
import usePreferences from '~/hooks/use-preferences';
import { Switch } from '../ui/switch';

export default function SimulationOptions() {
  const { state, engine } = useSimulation();
  const { t } = usePreferences();
  const { showAllRoutes, clusterStations } = state;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="pointer-events-auto h-10 w-10"
          aria-label="Toggle display options"
          aria-expanded={false}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
          <div
            className="flex items-center justify-between w-full cursor-pointer"
            onClick={() => engine.toggleShowAllRoutes()}
            role="switch"
            aria-checked={showAllRoutes}
            aria-label="Show all vehicle routes"
          >
            <span>{t.map.labels.showAllRoutes}</span>
            <Switch checked={showAllRoutes} />
          </div>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
          <div
            className="flex items-center justify-between w-full cursor-pointer"
            onClick={() => engine.toggleClusterStations()}
            role="switch"
            aria-checked={clusterStations}
            aria-label="Cluster nearby stations"
          >
            <span>{t.map.labels.clusterStations}</span>
            <Switch checked={clusterStations} />
          </div>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
