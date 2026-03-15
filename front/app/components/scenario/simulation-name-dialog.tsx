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

import { useEffect, useRef, useState } from 'react';
import { Button } from '~/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '~/components/ui/dialog';
import { Label } from '~/components/ui/label';
import { Input } from '~/components/ui/input';
import { Loader2 } from 'lucide-react';
import usePreferences from '~/hooks/use-preferences';

interface SimulationNameDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scenarioName: string;
  onStartSimulation: (simulationName: string) => void;
  startingSimulation: boolean;
}

export default function SimulationNameDialog({
  open,
  onOpenChange,
  scenarioName,
  onStartSimulation,
  startingSimulation,
}: SimulationNameDialogProps) {
  const { t } = usePreferences();
  const [name, setName] = useState(scenarioName);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setName(scenarioName);
      requestAnimationFrame(() => inputRef.current?.select());
    }
  }, [open, scenarioName]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.scenario.dialog.simulationNameTitle}</DialogTitle>
          <DialogDescription>
            {t.scenario.dialog.simulationNameDescription}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="simulation-name">
              {t.scenario.dialog.simulationNameLabel}
            </Label>
            <Input
              ref={inputRef}
              id="simulation-name"
              placeholder={t.scenario.dialog.simulationNamePlaceholder}
              value={name}
              onChange={(e) => setName(e.target.value)}
              onFocus={(e) => e.currentTarget.select()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && name.trim()) onStartSimulation(name);
              }}
              autoFocus
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} variant="outline">
            {t.common.cancel}
          </Button>
          <Button
            onClick={() => onStartSimulation(name)}
            disabled={!name.trim() || startingSimulation}
            data-testid="start-simulation-button"
          >
            {startingSimulation && <Loader2 className="animate-spin" />}
            {t.scenario.dialog.start}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
