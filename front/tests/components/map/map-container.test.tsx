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

import { expect, test } from 'vitest';
import { render } from '@testing-library/react';
import MapContainer from '~/components/map/map-container';
import { MapProvider } from '~/providers/map-provider';
import { SimulationProvider } from '~/providers/simulation-provider';
import { TaskAssignmentProvider } from '~/providers/task-assignment-provider';

test('map container render should fail without a map provider', async () => {
  expect(() => {
    render(<MapContainer />);
  }).toThrow('useMap must be used within a MapProvider');
});

test('map container render should succeed with a map provider', async () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );
  expect(getByTestId('map-container')).toBeDefined();
});
