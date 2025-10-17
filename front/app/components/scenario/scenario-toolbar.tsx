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

interface ScenarioToolbarProps {
  scenarioName: string;
  onNameChange: (name: string) => void;
  onImport: () => void;
  onNew: () => void;
}

export default function ScenarioToolbar({
  scenarioName,
  onNameChange,
  onImport,
  onNew,
}: ScenarioToolbarProps) {
  return (
    <div className="flex flex-col lg:flex-row gap-6 mb-6">
      <Input
        value={scenarioName}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder="Scenario name"
        className="flex-1"
        aria-label="Scenario name"
      />
      <div className="flex gap-2 w-full lg:w-64">
        <Button onClick={onImport} className="flex-1">
          Import
        </Button>
        <Button onClick={onNew} variant="destructive" className="flex-1">
          New
        </Button>
      </div>
    </div>
  );
}
