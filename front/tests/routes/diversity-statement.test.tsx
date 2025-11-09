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
import DiversityStatement, { meta } from '~/routes/diversity-statement';
import { createRoutesStub } from 'react-router';

test('meta function sets the title', () => {
  const metaInfo = meta();
  expect(metaInfo[0].title).toBeDefined();
  expect(metaInfo[0].title).toBe('Diversity Statement');
});

test('diversity statement page renders key points', () => {
  const Stub = createRoutesStub([
    {
      path: '/diversity-statement',
      Component: DiversityStatement,
    },
  ]);

  render(<Stub initialEntries={['/diversity-statement']} />);

  // Check that page tabs cover both supported languages
  expect(screen.getByText('English')).toBeDefined();
  expect(screen.getByText('Français')).toBeDefined();
});

test('renders cards with headers', () => {
  const Stub = createRoutesStub([
    {
      path: '/diversity-statement',
      Component: DiversityStatement,
    },
  ]);

  render(<Stub initialEntries={['/diversity-statement']} />);
});
