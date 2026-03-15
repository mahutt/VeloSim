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

import { Input } from '~/components/ui/input';
import { Button } from '~/components/ui/button';
import usePreferences from '~/hooks/use-preferences';

interface ScenarioToolbarProps {
  scenarioName: string;
  onNameChange: (name: string) => void;
  onImport: () => void;
  onNew: () => void;
  isEditMode: boolean;
  isExistingScenario: boolean;
}

export default function ScenarioToolbar({
  scenarioName,
  onNameChange,
  onImport,
  onNew,
  isEditMode,
  isExistingScenario,
}: ScenarioToolbarProps) {
  const { t } = usePreferences();

  return (
    <div className="flex flex-col gap-4 mb-6 sm:flex-row sm:items-end sm:gap-6">
      <div className="flex gap-2 w-full mb-2 sm:mb-0 sm:w-64 sm:order-2">
        <Button onClick={onImport} variant="outline" className="flex-1">
          {t.scenario.import}
        </Button>
        <Button onClick={onNew} className="flex-1">
          {t.scenario.new}
        </Button>
      </div>
      <Input
        value={scenarioName}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder={t.scenario.name}
        className="flex-1 sm:order-1"
        aria-label={t.scenario.name}
        disabled={isExistingScenario && !isEditMode}
      />
    </div>
  );
}
