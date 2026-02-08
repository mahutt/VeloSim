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
import { Textarea } from '~/components/ui/textarea';
import { Field, FieldLabel } from '~/components/ui/field';
import ScenarioContentOptions from './scenario-content-options';
import type { Dispatch, SetStateAction } from 'react';
import { useRef } from 'react';

interface ScenarioTextAreaProps {
  scenarioData: string;
  scenarioDescription: string;
  onDescriptionChange: (desc: string) => void;
  onChange: Dispatch<SetStateAction<string>>;
  onSave: () => void;
  onExport: () => void;
  onStart: () => void;
  isEditMode: boolean;
  isExistingScenario: boolean;
  onEdit: () => void;
}

export default function ScenarioTextArea({
  scenarioData,
  scenarioDescription,
  onDescriptionChange,
  onChange,
  onSave,
  onExport,
  onStart,
  isEditMode,
  isExistingScenario,
  onEdit,
}: ScenarioTextAreaProps) {
  const isDisabled = isExistingScenario && !isEditMode;
  const lineNumbersRef = useRef<HTMLDivElement>(null);

  // Calculate line numbers based on content
  const lineCount = scenarioData.split('\n').length;
  const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

  const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
    if (lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = e.currentTarget.scrollTop;
    }
  };

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
    <div className="flex-1 flex flex-col h-[40rem]">
      <Field data-disabled={isDisabled}>
        <FieldLabel htmlFor="scenario-description">Description</FieldLabel>
        <Textarea
          id="scenario-description"
          value={scenarioDescription}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Enter scenario description"
          className="h-20 resize-none font-mono"
          disabled={isDisabled}
        />
      </Field>

      <Field data-disabled={isDisabled} className="mt-4">
        <div className="flex items-center justify-between">
          <FieldLabel htmlFor="scenario-json">Scenario JSON</FieldLabel>
          <ScenarioContentOptions
            scenarioContent={scenarioData}
            setScenarioContent={onChange}
            onEdit={onEdit}
          />
        </div>
        <div className="flex h-[28rem] border rounded-md overflow-hidden bg-background">
          {/* Line numbers */}
          <div
            ref={lineNumbersRef}
            className="select-none overflow-hidden bg-muted/50 px-2 py-2 font-mono text-sm text-muted-foreground border-r min-w-12 text-right leading-6"
          >
            {lineNumbers.map((num) => (
              <div key={num} className="h-6">
                {num}
              </div>
            ))}
          </div>
          {/* Textarea */}
          <Textarea
            id="scenario-json"
            className="flex-1 h-full resize-none font-mono border-0 focus-visible:ring-0 focus-visible:ring-offset-0 rounded-none overflow-y-auto leading-6"
            placeholder="Paste or type your JSON scenario here..."
            value={scenarioData}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onScroll={handleScroll}
            disabled={isDisabled}
          />
        </div>
      </Field>

      <div className="flex flex-col gap-2 mt-4 sm:flex-row sm:justify-between sm:items-center">
        <div className="flex flex-col gap-2 w-full sm:flex-row sm:w-auto">
          {isExistingScenario && !isEditMode ? (
            <Button onClick={onEdit} className="w-full sm:w-32">
              Edit
            </Button>
          ) : (
            <Button onClick={onSave} className="w-full sm:w-32">
              Save
            </Button>
          )}
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
