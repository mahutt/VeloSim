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
import { log, LogContext, LogLevel } from '~/lib/logger';
import { MONTREAL_BOUNDS, SCHEDULED_TASK_PATTERN } from '~/constants';

interface AddStationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (station: {
    name: string;
    latitude: number;
    longitude: number;
    initialTaskCount?: number;
    scheduledTasks?: string[];
  }) => void;
}

export default function AddStationDialog({
  open,
  onOpenChange,
  onSubmit,
}: AddStationDialogProps) {
  const [name, setName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [initialTaskCount, setInitialTaskCount] = useState('');
  const [scheduledTasks, setScheduledTasks] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) {
      // Reset form when dialog closes
      setName('');
      setLatitude('');
      setLongitude('');
      setInitialTaskCount('');
      setScheduledTasks('');
      setErrors({});
    }
  }, [open]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = 'Station name is required';
    }

    const lat = parseFloat(latitude);
    if (!latitude || isNaN(lat)) {
      newErrors.latitude = 'Valid latitude is required';
    } else if (lat < MONTREAL_BOUNDS.LAT_MIN || lat > MONTREAL_BOUNDS.LAT_MAX) {
      newErrors.latitude = `must be between ${MONTREAL_BOUNDS.LAT_MIN} and ${MONTREAL_BOUNDS.LAT_MAX}`;
    }

    const lon = parseFloat(longitude);
    if (!longitude || isNaN(lon)) {
      newErrors.longitude = 'Valid longitude is required';
    } else if (lon < MONTREAL_BOUNDS.LON_MIN || lon > MONTREAL_BOUNDS.LON_MAX) {
      newErrors.longitude = `must be between ${MONTREAL_BOUNDS.LON_MIN} and ${MONTREAL_BOUNDS.LON_MAX}`;
    }

    if (initialTaskCount.trim()) {
      const taskCount = parseInt(initialTaskCount, 10);
      if (isNaN(taskCount) || taskCount < 0) {
        newErrors.initialTaskCount = 'Must be a non-negative number';
      }
    }

    if (scheduledTasks.trim()) {
      const tasks = scheduledTasks
        .split(',')
        .map((task) => task.trim())
        .filter((task) => task.length > 0);

      for (const task of tasks) {
        if (!SCHEDULED_TASK_PATTERN.test(task)) {
          newErrors.scheduledTasks = `Invalid format: "${task}". Must be dayN:HH:MM (e.g., day1:09:30)`;
          break;
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      log({
        message: 'Station form validation failed',
        level: LogLevel.WARNING,
        context: LogContext.AddStationDialog,
        entityType: 'station',
      });
      return;
    }

    const tasks = scheduledTasks
      .split(',')
      .map((task) => task.trim())
      .filter((task) => task.length > 0);

    const stationData = {
      name: name.trim(),
      latitude: parseFloat(latitude),
      longitude: parseFloat(longitude),
      initialTaskCount: initialTaskCount
        ? parseInt(initialTaskCount, 10)
        : undefined,
      scheduledTasks: tasks.length > 0 ? tasks : undefined,
    };

    log({
      message: `Station form submitted: ${stationData.name}`,
      level: LogLevel.INFO,
      context: LogContext.AddStationDialog,
      entityType: 'station',
    });

    onSubmit(stationData);

    // Reset form
    setName('');
    setLatitude('');
    setLongitude('');
    setInitialTaskCount('');
    setScheduledTasks('');
    setErrors({});
    onOpenChange(false);
  };

  const handleCancel = () => {
    setName('');
    setLatitude('');
    setLongitude('');
    setInitialTaskCount('');
    setScheduledTasks('');
    setErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add Station</DialogTitle>
          <DialogDescription>
            Configure a new station to insert into the scenario.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Station Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Main Street Station"
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
              <Label htmlFor="latitude">Latitude</Label>
              <Input
                id="latitude"
                type="number"
                step="any"
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                placeholder="e.g., 45.5017"
                aria-invalid={!!errors.latitude}
                aria-describedby={
                  errors.latitude ? 'latitude-error' : undefined
                }
              />
              {errors.latitude && (
                <p id="latitude-error" className="text-sm text-destructive">
                  {errors.latitude}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="longitude">Longitude</Label>
              <Input
                id="longitude"
                type="number"
                step="any"
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                placeholder="e.g., -73.5673"
                aria-invalid={!!errors.longitude}
                aria-describedby={
                  errors.longitude ? 'longitude-error' : undefined
                }
              />
              {errors.longitude && (
                <p id="longitude-error" className="text-sm text-destructive">
                  {errors.longitude}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="scheduledTasks">Scheduled Tasks (optional)</Label>
              <Input
                id="scheduledTasks"
                value={scheduledTasks}
                onChange={(e) => setScheduledTasks(e.target.value)}
                placeholder="e.g., day1:09:30, day1:14:00, day2:10:15"
                aria-invalid={!!errors.scheduledTasks}
                aria-describedby={
                  errors.scheduledTasks
                    ? 'scheduledTasks-error'
                    : 'scheduledTasks-hint'
                }
              />
              {errors.scheduledTasks && (
                <p
                  id="scheduledTasks-error"
                  className="text-sm text-destructive"
                >
                  {errors.scheduledTasks}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="initialTaskCount">
                Initial Task Count (optional)
              </Label>
              <Input
                id="initialTaskCount"
                type="number"
                min="0"
                value={initialTaskCount}
                onChange={(e) => setInitialTaskCount(e.target.value)}
                placeholder="e.g., 5"
                aria-invalid={!!errors.initialTaskCount}
                aria-describedby={
                  errors.initialTaskCount ? 'initialTaskCount-error' : undefined
                }
              />
              {errors.initialTaskCount && (
                <p
                  id="initialTaskCount-error"
                  className="text-sm text-destructive"
                >
                  {errors.initialTaskCount}
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button type="submit">Add Station</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
