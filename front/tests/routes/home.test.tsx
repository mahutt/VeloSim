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
import { render, screen } from '@testing-library/react';
import Home, { meta } from '~/routes/home';
import { createRoutesStub } from 'react-router';

test('meta function sets all fields', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
  expect(metaInfo[1].name).toBeDefined();
  expect(metaInfo[1].content).toBeDefined();
});

test('home pages loads 1 button', async () => {
  const Stub = createRoutesStub([
    {
      path: '/',
      Component: Home,
    },
  ]);

  render(<Stub initialEntries={['/']} />);
  expect(screen.getAllByRole('button')).toHaveLength(1);
});
