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

import { useState, type Dispatch, type SetStateAction } from 'react';
import { DropdownMenuItem } from '../ui/dropdown-menu';
import { toast } from 'sonner';
import AddVehicleDialog from './add-vehicle-dialog';

interface AddVehicleButtonProps {
  scenarioContent: string;
  setScenarioContent: Dispatch<SetStateAction<string>>;
  onEdit: () => void;
}

export default function AddVehicleButton({
  scenarioContent,
  setScenarioContent,
  onEdit,
}: AddVehicleButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleAddVehicle = (vehicleData: {
    name: string;
    latitude?: number;
    longitude?: number;
    batteryCount?: number;
  }) => {
    onEdit(); // Switch to edit mode

    const newVehicle: {
      name: string;
      position?: [number, number];
      battery_count?: number;
    } = {
      name: vehicleData.name,
    };

    // Only include position if both latitude and longitude are provided
    if (
      vehicleData.latitude !== undefined &&
      vehicleData.longitude !== undefined
    ) {
      newVehicle.position = [vehicleData.longitude, vehicleData.latitude];
    }

    if (vehicleData.batteryCount !== undefined) {
      newVehicle.battery_count = vehicleData.batteryCount;
    }

    setScenarioContent((prev) => {
      let jsonNew;
      try {
        const jsonPrev = JSON.parse(prev);
        const existingVehicles = Array.isArray(jsonPrev.vehicles)
          ? jsonPrev.vehicles
          : [];

        jsonNew = {
          ...jsonPrev,
          vehicles: [...existingVehicles, newVehicle],
        };
      } catch {
        // If parsing fails, create new scenario with just this vehicle
        toast.warning(
          'Failed to parse existing scenario - creating new scenario'
        );
        jsonNew = {
          vehicles: [newVehicle],
        };
      }
      return JSON.stringify(jsonNew, null, 2);
    });

    toast.success(`Vehicle "${vehicleData.name}" added successfully`);
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
        Add Vehicle
      </DropdownMenuItem>
      <AddVehicleDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={handleAddVehicle}
        scenarioContent={scenarioContent}
      />
    </>
  );
}
