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
import type { Resource } from '~/types';

export default function ResourceBar() {
  const placeholderResources: Resource[] = [
    {
      resourceId: '1',
      position: [-74.006, 40.7128],
      taskList: [101, 102],
      routeId: '',
    },
    {
      resourceId: '2',
      position: [-74.0059, 40.7138],
      taskList: [103],
      routeId: '',
    },
    {
      resourceId: '3',
      position: [-74.0055, 40.7148],
      taskList: [],
      routeId: '',
    },
    {
      resourceId: '4',
      position: [-74.0045, 40.7158],
      taskList: [104, 105, 106],
      routeId: '',
    },
    {
      resourceId: '5',
      position: [-74.0035, 40.7168],
      taskList: [107],
      routeId: '',
    },
    {
      resourceId: '6',
      position: [-74.0025, 40.7178],
      taskList: [108, 109],
      routeId: '',
    },
    {
      resourceId: '7',
      position: [-74.0015, 40.7188],
      taskList: [],
      routeId: '',
    },
    {
      resourceId: '8',
      position: [-74.0005, 40.7198],
      taskList: [110],
      routeId: '',
    },
    {
      resourceId: '9',
      position: [-73.9995, 40.7208],
      taskList: [111, 112],
      routeId: '',
    },
    {
      resourceId: '10',
      position: [-73.9985, 40.7218],
      taskList: [113],
      routeId: '',
    },
  ];

  return (
    <div className="absolute top-4 right-4 w-60 bg-gray-300 shadow rounded p-4">
      <div className="space-y-2">
        {placeholderResources.map((resource) => (
          <ResourceItem
            key={resource.resourceId}
            resourceId={resource.resourceId}
            resource={resource}
            onSelect={(resourceId) => console.log(resourceId)}
            // logging the selection for now
            // can replace with modal or other action later
          />
        ))}
      </div>
    </div>
  );
}
