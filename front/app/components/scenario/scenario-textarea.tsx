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

import { Button } from '~/components/ui/button';

interface ScenarioTextAreaProps {
  scenarioData: string;
  error: string | null;
  onChange: (data: string) => void;
  onSave: () => void;
  onExport: () => void;
  onStart: () => void;
}

export default function ScenarioTextArea({
  scenarioData,
  error,
  onChange,
  onSave,
  onExport,
  onStart,
}: ScenarioTextAreaProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Allow Tab key to insert spaces for indentation
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;

      // Insert 2 spaces at cursor position
      const newValue =
        scenarioData.substring(0, start) + '  ' + scenarioData.substring(end);

      onChange(newValue);

      // Move cursor after the inserted spaces
      setTimeout(() => {
        target.selectionStart = target.selectionEnd = start + 2;
      }, 0);
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <textarea
        className="w-full h-[32rem] p-3 border rounded-md font-mono text-sm mb-4 resize-none overflow-y-auto"
        placeholder="Paste or type your JSON scenario here..."
        value={scenarioData}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-label="Scenario JSON data"
      />

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-600 text-sm">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-2 mt-4 sm:flex-row sm:justify-between sm:items-center">
        <div className="flex flex-col gap-2 w-full sm:flex-row sm:w-auto">
          <Button onClick={onSave} className="w-full sm:w-32">
            Save
          </Button>
          <Button
            onClick={onExport}
            variant="outline"
            className="w-full sm:w-32"
          >
            Export
          </Button>
        </div>
        <Button onClick={onStart} className="w-full sm:w-32">
          Start Simulation
        </Button>
      </div>
    </div>
  );
}
