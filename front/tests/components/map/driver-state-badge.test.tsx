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
import { describe, it, expect } from 'vitest';
import DriverStateBadge from '~/components/map/driver-state-badge';
import { DriverState } from '~/types';

describe('DriverStateBadge', () => {
  it('renders off shift state correctly', () => {
    render(<DriverStateBadge state={DriverState.OffShift} />);

    expect(screen.getByText('Off shift')).toBeInTheDocument();
  });

  it('renders pending shift state correctly', () => {
    render(<DriverStateBadge state={DriverState.PendingShift} />);

    expect(screen.getByText('Pending shift')).toBeInTheDocument();
  });

  it('renders idle state correctly', () => {
    render(<DriverStateBadge state={DriverState.Idle} />);

    expect(screen.getByText('Idle')).toBeInTheDocument();
  });

  it('renders on route state correctly', () => {
    render(<DriverStateBadge state={DriverState.OnRoute} />);

    expect(screen.getByText('On route')).toBeInTheDocument();
  });

  it('renders servicing station state correctly', () => {
    render(<DriverStateBadge state={DriverState.ServicingStation} />);
    expect(screen.getByText('Servicing')).toBeInTheDocument();
  });

  it('renders on break state correctly', () => {
    render(<DriverStateBadge state={DriverState.OnBreak} />);

    expect(screen.getByText('On break')).toBeInTheDocument();
  });

  it('renders ending shift state correctly', () => {
    render(<DriverStateBadge state={DriverState.EndingShift} />);

    expect(screen.getByText('Ending shift')).toBeInTheDocument();
  });

  it('renders seeking HQ state correctly', () => {
    render(<DriverStateBadge state={DriverState.SeekingHQForInventory} />);

    expect(screen.getByText('Returning for restock')).toBeInTheDocument();
  });

  it('renders restocking batteries state correctly', () => {
    render(<DriverStateBadge state={DriverState.RestockingBatteries} />);

    expect(screen.getByText('Restocking')).toBeInTheDocument();
  });
});
