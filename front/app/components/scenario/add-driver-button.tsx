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

import {
  useState,
  type Dispatch,
  type SetStateAction,
  type ReactNode,
} from 'react';
import { DropdownMenuItem } from '../ui/dropdown-menu';
import { toast } from 'sonner';
import AddDriverDialog from './add-driver-dialog';

interface AddDriverButtonProps {
  setScenarioContent: Dispatch<SetStateAction<string>>;
  onEdit: () => void;
  icon?: ReactNode;
}

export default function AddDriverButton({
  setScenarioContent,
  onEdit,
  icon,
}: AddDriverButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleAddDriver = (driverData: {
    name: string;
    shift: {
      start_time: string;
      end_time: string;
      lunch_break?: string;
    };
  }) => {
    onEdit(); // Switch to edit mode

    const newDriver: {
      name: string;
      shift: {
        start_time: string;
        end_time: string;
        lunch_break?: string;
      };
    } = {
      name: driverData.name,
      shift: driverData.shift,
    };

    setScenarioContent((prev) => {
      let jsonNew;
      try {
        const jsonPrev = JSON.parse(prev);
        const existingDrivers = Array.isArray(jsonPrev.drivers)
          ? jsonPrev.drivers
          : [];

        jsonNew = {
          ...jsonPrev,
          drivers: [...existingDrivers, newDriver],
        };
      } catch {
        // If parsing fails, create new scenario with just this driver
        jsonNew = {
          drivers: [newDriver],
        };
      }
      return JSON.stringify(jsonNew, null, 2);
    });

    toast.success(`Driver "${driverData.name}" added successfully`);
    setDialogOpen(false);
    setDialogOpen(false);
  };

  return (
    <>
      <DropdownMenuItem
        onSelect={(e) => {
          e.preventDefault();
          setDialogOpen(true);
        }}
      >
        {icon}
        Add Driver
      </DropdownMenuItem>
      <AddDriverDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={handleAddDriver}
      />
    </>
  );
}
