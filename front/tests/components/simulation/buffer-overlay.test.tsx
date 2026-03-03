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

import { render, screen } from '@testing-library/react';
import { makeReactiveSimulationState } from 'tests/test-helpers';
import { vi, describe, it, expect, afterEach, type Mock } from 'vitest';
import BufferOverlay from '~/components/simulation/buffer-overlay';
import { useSimulation } from '~/providers/simulation-provider';

vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: vi.fn(),
}));

describe('BufferOverlay', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('displays loader when sim is buffering', () => {
    (useSimulation as Mock).mockReturnValue({
      state: makeReactiveSimulationState({
        isBuffering: true,
      }),
    });

    render(<BufferOverlay />);

    expect(screen.getByTestId('buffer-loader')).toBeInTheDocument();
  });

  it("displays nothing when sim isn't buffering", () => {
    (useSimulation as Mock).mockReturnValue({
      state: makeReactiveSimulationState({
        isBuffering: false,
      }),
    });

    render(<BufferOverlay />);

    expect(screen.queryByTestId('buffer-loader')).not.toBeInTheDocument();
  });
});
