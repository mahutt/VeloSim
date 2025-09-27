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
import {
  INITIAL_CENTER,
  INITIAL_ZOOM,
  MapProvider,
} from '~/providers/map-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';

test('map provider instantiates mapboxgl Map instance in presence of map container', async () => {
  render(
    <MapProvider>
      <MapContainer />
    </MapProvider>
  );
  const map = MockMap.instance;
  expect(map).toBeDefined();
  expect(map!.getCenter()).toBe(INITIAL_CENTER);
  expect(map!.getZoom()).toBe(INITIAL_ZOOM);
});

test("map provider doesn't instantiate mapboxgl Map instance without map container", async () => {
  render(
    <MapProvider>
      <div />
    </MapProvider>
  );
  const map = MockMap.instance;
  expect(map).toBeUndefined();
});
