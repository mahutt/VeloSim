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

interface AddDriverDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (driver: {
    name: string;
    shift: {
      start_time: string;
      end_time: string;
      lunch_break?: string;
    };
  }) => void;
}

export default function AddDriverDialog({
  open,
  onOpenChange,
  onSubmit,
}: AddDriverDialogProps) {
  const [name, setName] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [lunchBreak, setLunchBreak] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!open) {
      // Reset form when dialog closes
      setName('');
      setStartTime('');
      setEndTime('');
      setLunchBreak('');
      setErrors({});
    }
  }, [open]);

  const validateTimeFormat = (time: string): boolean => {
    // Format: dayN:HH:MM (e.g., day1:08:00)
    const timePattern = /^day\d+:\d{2}:\d{2}$/;
    return timePattern.test(time);
  };

  const parseTime = (
    time: string
  ): { day: number; hours: number; minutes: number } | null => {
    const match = time.match(/^day(\d+):(\d{2}):(\d{2})$/);
    if (!match) return null;
    return {
      day: parseInt(match[1], 10),
      hours: parseInt(match[2], 10),
      minutes: parseInt(match[3], 10),
    };
  };

  const compareTime = (time1: string, time2: string): number => {
    const t1 = parseTime(time1);
    const t2 = parseTime(time2);
    if (!t1 || !t2) return 0;

    if (t1.day !== t2.day) return t1.day - t2.day;
    if (t1.hours !== t2.hours) return t1.hours - t2.hours;
    return t1.minutes - t2.minutes;
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = 'Driver name is required';
    }

    if (!startTime.trim()) {
      newErrors.startTime = 'Start time is required';
    } else if (!validateTimeFormat(startTime.trim())) {
      newErrors.startTime = 'Invalid format. Use dayN:HH:MM (e.g., day1:08:00)';
    }

    if (!endTime.trim()) {
      newErrors.endTime = 'End time is required';
    } else if (!validateTimeFormat(endTime.trim())) {
      newErrors.endTime = 'Invalid format. Use dayN:HH:MM (e.g., day1:17:00)';
    }

    // Check if end time is after start time
    if (
      startTime.trim() &&
      endTime.trim() &&
      validateTimeFormat(startTime.trim()) &&
      validateTimeFormat(endTime.trim())
    ) {
      if (compareTime(endTime.trim(), startTime.trim()) <= 0) {
        newErrors.endTime = 'End time must be after start time';
      }
    }

    if (lunchBreak.trim()) {
      if (!validateTimeFormat(lunchBreak.trim())) {
        newErrors.lunchBreak =
          'Invalid format. Use dayN:HH:MM (e.g., day1:12:00)';
      } else if (
        startTime.trim() &&
        endTime.trim() &&
        validateTimeFormat(startTime.trim()) &&
        validateTimeFormat(endTime.trim())
      ) {
        // Check if lunch break is between start and end time
        const lunchTrimmed = lunchBreak.trim();
        if (
          compareTime(lunchTrimmed, startTime.trim()) <= 0 ||
          compareTime(lunchTrimmed, endTime.trim()) >= 0
        ) {
          newErrors.lunchBreak =
            'Lunch break must be between start and end time';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const shift: {
      start_time: string;
      end_time: string;
      lunch_break?: string;
    } = {
      start_time: startTime.trim(),
      end_time: endTime.trim(),
    };

    if (lunchBreak.trim()) {
      shift.lunch_break = lunchBreak.trim();
    }

    onSubmit({
      name: name.trim(),
      shift,
    });

    // Reset form
    setName('');
    setStartTime('');
    setEndTime('');
    setLunchBreak('');
    setErrors({});
  };

  const handleCancel = () => {
    setName('');
    setStartTime('');
    setEndTime('');
    setLunchBreak('');
    setErrors({});
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Driver</DialogTitle>
          <DialogDescription>
            Configure a new driver to insert into the scenario.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Driver Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Driver 1"
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
              <Label htmlFor="startTime">Shift Start Time</Label>
              <Input
                id="startTime"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                placeholder="e.g., day1:08:00"
                aria-invalid={!!errors.startTime}
                aria-describedby={
                  errors.startTime ? 'startTime-error' : undefined
                }
              />
              {errors.startTime && (
                <p id="startTime-error" className="text-sm text-destructive">
                  {errors.startTime}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="endTime">Shift End Time</Label>
              <Input
                id="endTime"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                placeholder="e.g., day1:17:00"
                aria-invalid={!!errors.endTime}
                aria-describedby={errors.endTime ? 'endTime-error' : undefined}
              />
              {errors.endTime && (
                <p id="endTime-error" className="text-sm text-destructive">
                  {errors.endTime}
                </p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="lunchBreak">Lunch Break (optional)</Label>
              <Input
                id="lunchBreak"
                value={lunchBreak}
                onChange={(e) => setLunchBreak(e.target.value)}
                placeholder="e.g., day1:12:00"
                aria-invalid={!!errors.lunchBreak}
                aria-describedby={
                  errors.lunchBreak ? 'lunchBreak-error' : undefined
                }
              />
              {errors.lunchBreak && (
                <p id="lunchBreak-error" className="text-sm text-destructive">
                  {errors.lunchBreak}
                </p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button type="submit">Add Driver</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
