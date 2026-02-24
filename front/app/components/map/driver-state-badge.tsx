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

import { DriverState } from '~/types';
import { Badge } from '../ui/badge';
import { useState } from 'react';

interface DriverStateBadgeProps {
  state: DriverState;
  shortened?: boolean;
}

export default function DriverStateBadge({
  state,
  shortened = false,
}: DriverStateBadgeProps) {
  const [isHovering, setIsHovering] = useState(false);
  let className = '';
  let label = '';
  let shortenedLabel = '';
  switch (state) {
    case DriverState.OffShift:
      className = 'bg-gray-200';
      label = 'Off shift';
      shortenedLabel = 'Off';
      break;
    case DriverState.PendingShift:
      className = 'bg-blue-200';
      label = 'Pending shift';
      shortenedLabel = 'Pending';
      break;
    case DriverState.Idle:
      className = 'bg-green-200';
      label = 'Idle';
      shortenedLabel = 'Idle';
      break;
    case DriverState.OnRoute:
      className = 'bg-yellow-200';
      label = 'On route';
      shortenedLabel = 'On route';
      break;
    case DriverState.ServicingStation:
      className = 'bg-purple-200';
      label = 'Servicing';
      shortenedLabel = 'Servicing';
      break;
    case DriverState.OnBreak:
      className = 'bg-orange-200';
      label = 'On break';
      shortenedLabel = 'Break';
      break;
    case DriverState.EndingShift:
      className = 'bg-red-200';
      label = 'Ending shift';
      shortenedLabel = 'Ending';
      break;
    case DriverState.SeekingHQForInventory:
      className = 'bg-indigo-200';
      label = 'Returning for restock';
      shortenedLabel = 'Return';
      break;
    case DriverState.RestockingBatteries:
      className = 'bg-teal-200';
      label = 'Restocking';
      shortenedLabel = 'Restock';
      break;
  }

  return (
    <Badge
      variant="secondary"
      className={`${className}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {(() => {
        if (!shortened) return label;
        return isHovering ? label : shortenedLabel;
      })()}
    </Badge>
  );
}
