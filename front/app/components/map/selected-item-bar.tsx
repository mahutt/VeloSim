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

import { X } from 'lucide-react';
import { Button } from '~/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '~/components/ui/card';
import { Separator } from '~/components/ui/separator';
import { useSimulationContext } from '~/providers/simulation-provider';
import { SelectedItemType, type Station, type Resource } from '~/types';

export default function SelectedItemBar() {
  const { selectedItem, clearSelection } = useSimulationContext();

  if (!selectedItem) return null;

  const handleClose = () => {
    clearSelection();
  };

  return (
    <div className="absolute top-4 left-4 z-10 w-80">
      <Card className="bg-gray-50">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-lg font-semibold">
            <span className="text-red-500">
              {selectedItem.type === SelectedItemType.Station
                ? 'Station'
                : 'Resource'}
            </span>{' '}
            <span className="text-foreground">
              {selectedItem.type === SelectedItemType.Station
                ? `#${(selectedItem.value as Station).id}`
                : `#${(selectedItem.value as Resource).id}`}
            </span>
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleClose}
            className="h-6 w-6"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <Separator />
        <CardContent>
          {selectedItem.type === SelectedItemType.Station ? (
            <StationInfo station={selectedItem.value as Station} />
          ) : (
            <ResourceInfo resource={selectedItem.value as Resource} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StationInfo({ station }: { station: Station }) {
  return (
    <div className="space-y-2">
      <div>
        <p className="text-sm text-muted-foreground">Name</p>
        <p className="text-sm">{station.name}</p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">Position</p>
        <p className="font-mono text-xs">
          [{station.position[0].toFixed(5)}, {station.position[1].toFixed(5)}]
        </p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">
          Tasks ({station.tasks.length})
        </p>
        <p className="text-sm">
          {station.tasks.length > 0
            ? station.tasks
                .map((task) => task.type.replace('_', ' '))
                .join(', ')
            : 'No tasks assigned'}
        </p>
      </div>
    </div>
  );
}

function ResourceInfo({ resource }: { resource: Resource }) {
  return (
    <div className="space-y-2">
      <div>
        <p className="text-sm text-muted-foreground">Position</p>
        <p className="font-mono text-xs">
          [{resource.position[0].toFixed(5)}, {resource.position[1].toFixed(5)}]
        </p>
      </div>
      <div>
        <p className="text-sm text-muted-foreground">
          Tasks ({resource.taskList.length})
        </p>
        <p className="text-sm">
          {resource.taskList.length > 0
            ? resource.taskList.map((id) => `${id}`).join(', ')
            : 'No tasks assigned'}
        </p>
      </div>
    </div>
  );
}
