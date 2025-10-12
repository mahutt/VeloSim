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

import { ResourceItem } from './resource-item';
import { useSimulation } from '~/providers/simulation-provider';
import { SelectedItemType } from '~/types';
import { Card, CardContent } from '~/components/ui/card';
import { SearchBar } from '~/components/ui/search-bar';
import { useMemo, useState } from 'react';

export default function ResourceBar() {
  const { selectItem, resources, selectedItem } = useSimulation();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSelect = (resourceId: number) => {
    selectItem(SelectedItemType.Resource, resourceId);
  };

  // Check if a resource is currently selected
  const isResourceSelected = (resourceId: number) => {
    return (
      selectedItem?.type === SelectedItemType.Resource &&
      selectedItem.value.id === resourceId
    );
  };

  // Filter resources based on their ID
  const filteredResources = useMemo(() => {
    if (!searchQuery.trim()) {
      return resources;
    }

    const query = searchQuery.toLowerCase();
    return resources.filter((resource) => {
      const resourceIdString = resource.id.toString();
      const resourceMatch =
        resourceIdString === query || resourceIdString.startsWith(query);

      return resourceMatch;
    });
  }, [resources, searchQuery]);

  return (
    <div className="absolute top-4 right-4 w-60 max-h-[calc(100vh-2rem)]">
      <Card className="bg-gray-50 gap-0">
        <div className="px-6 pb-3">
          <SearchBar
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onClear={() => setSearchQuery('')}
            placeholder="Search Resource"
          />
        </div>
        <CardContent className="pt-0">
          <div className="space-y-2 max-h-[calc(100vh-12rem)] overflow-y-auto pr-3 -mr-3">
            {filteredResources.map((resource) => (
              <ResourceItem
                key={resource.id}
                resource={resource}
                onSelect={() => handleSelect(resource.id)}
                isSelected={isResourceSelected(resource.id)}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
