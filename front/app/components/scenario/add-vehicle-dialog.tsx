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

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';
import { Button } from '~/components/ui/button';
import { Input } from '~/components/ui/input';
import { Label } from '~/components/ui/label';
import { toast } from 'sonner';
import { MONTREAL_BOUNDS } from '~/constants';

interface AddVehicleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (vehicle: {
    name: string;
    latitude?: number;
    longitude?: number;
    batteryCount?: number;
  }) => void;
  scenarioContent: string;
}

export default function AddVehicleDialog({
  open,
  onOpenChange,
  onSubmit,
  scenarioContent,
}: AddVehicleDialogProps) {
  const [name, setName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [batteryCount, setBatteryCount] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) {
      // Reset form when dialog closes
      setName('');
      setLatitude('');
      setLongitude('');
      setBatteryCount('');
      setErrors({});
    }
  }, [open]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = 'Vehicle name is required';
    }

    // If latitude or longitude is provided, both must be provided and valid
    const hasLat = latitude.trim().length > 0;
    const hasLon = longitude.trim().length > 0;

    if (hasLat || hasLon) {
      // Check if there are available drivers for vehicle with position
      try {
        const content = JSON.parse(scenarioContent);
        const drivers = content.drivers || [];
        const vehicles = content.vehicles || [];

        // Count vehicles that already have positions
        const vehiclesWithPosition = vehicles.filter(
          (v: { position?: unknown }) => v.position !== undefined
        ).length;

        // Check if adding this vehicle with position would exceed available drivers
        if (vehiclesWithPosition >= drivers.length) {
          newErrors.latitude = 'Insufficient drivers for positioned vehicle';
          newErrors.longitude = 'Insufficient drivers for positioned vehicle';
        }
      } catch {
        // If parsing fails, show a warning but allow the form
        toast.warning('Cannot validate drivers - invalid scenario format');
      }

      if (!hasLat) {
        newErrors.latitude = 'Latitude is required when longitude is provided';
      } else {
        const lat = parseFloat(latitude);
        if (isNaN(lat)) {
          newErrors.latitude = 'Valid latitude is required';
        } else if (lat < -90 || lat > 90) {
          newErrors.latitude = 'Latitude must be between -90 and 90';
        } else if (
          lat < MONTREAL_BOUNDS.LAT_MIN ||
          lat > MONTREAL_BOUNDS.LAT_MAX
        ) {
          newErrors.latitude = `Latitude is outside Greater Montreal Area bounds (must be between ${MONTREAL_BOUNDS.LAT_MIN} and ${MONTREAL_BOUNDS.LAT_MAX})`;
        }
      }

      if (!hasLon) {
        newErrors.longitude = 'Longitude is required when latitude is provided';
      } else {
        const lon = parseFloat(longitude);
        if (isNaN(lon)) {
          newErrors.longitude = 'Valid longitude is required';
        } else if (lon < -180 || lon > 180) {
          newErrors.longitude = 'Longitude must be between -180 and 180';
        } else if (
          lon < MONTREAL_BOUNDS.LON_MIN ||
          lon > MONTREAL_BOUNDS.LON_MAX
        ) {
          newErrors.longitude = `Longitude is outside Greater Montreal Area bounds (must be between ${MONTREAL_BOUNDS.LON_MIN} and ${MONTREAL_BOUNDS.LON_MAX})`;
        }
      }
    }

    if (batteryCount.trim()) {
      const count = parseInt(batteryCount, 10);
      if (isNaN(count) || count < 0) {
        newErrors.batteryCount = 'Must be a non-negative number';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error('Please fix the validation errors before submitting');
      return;
    }

    const vehicleData: {
      name: string;
      latitude?: number;
      longitude?: number;
      batteryCount?: number;
    } = {
      name: name.trim(),
    };

    // Only include position if both lat and lon are provided
    if (latitude.trim() && longitude.trim()) {
      vehicleData.latitude = parseFloat(latitude);
      vehicleData.longitude = parseFloat(longitude);
    }

    if (batteryCount.trim()) {
      vehicleData.batteryCount = parseInt(batteryCount, 10);
    }

    onSubmit(vehicleData);

    // Reset form
    setName('');
    setLatitude('');
    setLongitude('');
    setBatteryCount('');
    setErrors({});
  };

  const handleCancel = () => {
    setName('');
    setLatitude('');
    setLongitude('');
    setBatteryCount('');
    setErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Vehicle</DialogTitle>
          <DialogDescription>
            Configure a new vehicle to insert into the scenario.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Vehicle Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Vehicle 1"
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? 'name-error' : undefined}
              />
              {errors.name && (
                <p id="name-error" className="text-sm text-destructive">
                  {errors.name}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="latitude">Latitude (optional)</Label>
              <Input
                id="latitude"
                type="number"
                step="any"
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                placeholder="e.g., 45.5017"
                aria-invalid={!!errors.latitude}
                aria-describedby={
                  errors.latitude ? 'latitude-error' : 'latitude-hint'
                }
              />
              <p id="latitude-hint" className="text-xs text-muted-foreground">
                Range: {MONTREAL_BOUNDS.LAT_MIN} to {MONTREAL_BOUNDS.LAT_MAX}
              </p>
              {errors.latitude && (
                <p id="latitude-error" className="text-sm text-destructive">
                  {errors.latitude}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="longitude">Longitude (optional)</Label>
              <Input
                id="longitude"
                type="number"
                step="any"
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                placeholder="e.g., -73.5673"
                aria-invalid={!!errors.longitude}
                aria-describedby={
                  errors.longitude ? 'longitude-error' : 'longitude-hint'
                }
              />
              <p id="longitude-hint" className="text-xs text-muted-foreground">
                Range: {MONTREAL_BOUNDS.LON_MIN} to {MONTREAL_BOUNDS.LON_MAX}
              </p>
              {errors.longitude && (
                <p id="longitude-error" className="text-sm text-destructive">
                  {errors.longitude}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="batteryCount">Battery Count (optional)</Label>
              <Input
                id="batteryCount"
                type="number"
                min="0"
                value={batteryCount}
                onChange={(e) => setBatteryCount(e.target.value)}
                placeholder="e.g., 5"
                aria-invalid={!!errors.batteryCount}
                aria-describedby={
                  errors.batteryCount
                    ? 'batteryCount-error'
                    : 'batteryCount-hint'
                }
              />
              <p
                id="batteryCount-hint"
                className="text-xs text-muted-foreground"
              >
                Leave empty to start at HQ with 0 batteries. If position is
                provided, vehicle starts at that location.
              </p>
              {errors.batteryCount && (
                <p id="batteryCount-error" className="text-sm text-destructive">
                  {errors.batteryCount}
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button type="submit">Add Vehicle</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
