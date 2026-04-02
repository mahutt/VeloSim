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

import { ResourceItem, type ResourceItemElement } from './resource-item';
import { useSimulation } from '~/providers/simulation-provider';
import { Card, CardContent } from '~/components/ui/card';
import { SelectedItemType } from '../map/selected-item-bar';

// Restricted Resource[] type for ResourceBar component
export type ResourceBarElement = ResourceItemElement[];

export default function ResourceBar() {
  const { state, engine } = useSimulation();
  const { resourceBarElement, selectedItems } = state;

  const handleSelect = (resourceId: number) => {
    engine.selectItem(SelectedItemType.Driver, resourceId);
  };

  // Check if a resource is currently selected
  const isResourceSelected = (resourceId: number) => {
    return (
      selectedItems.length === 1 &&
      selectedItems[0].type === SelectedItemType.Driver &&
      selectedItems[0].value.id === resourceId
    );
  };

  return (
    <Card className="pointer-events-auto py-3 w-full min-h-0 bg-gray-50 gap-0 flex flex-col">
      <CardContent className="pt-0 px-3 flex-1 overflow-y-auto">
        <div className="space-y-2">
          {resourceBarElement.length === 0 ? (
            <div className="text-center text-muted-foreground py-8 select-none">
              No resources currently available
            </div>
          ) : (
            resourceBarElement.map((resource) => (
              <ResourceItem
                key={resource.id}
                resource={resource}
                onSelect={() => handleSelect(resource.id)}
                isSelected={isResourceSelected(resource.id)}
              />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
