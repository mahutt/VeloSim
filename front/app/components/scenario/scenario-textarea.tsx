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
import CodeMirror from '@uiw/react-codemirror';
import { json } from '@codemirror/lang-json';
import { EditorView, placeholder } from '@codemirror/view';

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

  // Custom theme to fix line number gutter width
  const fixedGutterTheme = EditorView.theme({
    '.cm-gutters': {
      minWidth: '3rem',
    },
    '.cm-lineNumbers': {
      minWidth: '2.5rem',
    },
  });

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
        <div
          className={`border rounded-md overflow-hidden h-[28rem] ${isDisabled ? 'bg-muted/50 opacity-60' : 'bg-background'}`}
        >
          <CodeMirror
            value={scenarioData}
            onChange={(value) => onChange(value)}
            extensions={[
              json(),
              EditorView.lineWrapping,
              fixedGutterTheme,
              placeholder('Paste or type your JSON scenario here...'),
            ]}
            editable={!isDisabled}
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: true,
              highlightSpecialChars: true,
              foldGutter: true,
              drawSelection: true,
              dropCursor: true,
              allowMultipleSelections: true,
              indentOnInput: true,
              bracketMatching: true,
              closeBrackets: true,
              autocompletion: true,
              rectangularSelection: true,
              highlightActiveLine: true,
              highlightSelectionMatches: true,
              closeBracketsKeymap: true,
              searchKeymap: true,
              foldKeymap: true,
              completionKeymap: true,
              lintKeymap: true,
            }}
            height="100%"
            className="h-full"
            style={{
              fontSize: '14px',
              height: '100%',
            }}
            theme={isDisabled ? 'light' : undefined}
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
