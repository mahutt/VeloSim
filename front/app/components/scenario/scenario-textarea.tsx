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
  onChange: (data: string) => void;
  onStart: () => void;
}

export default function ScenarioTextArea({
  scenarioData,
  onChange,
  onStart,
}: ScenarioTextAreaProps) {
  return (
    <div className="flex-1 flex flex-col">
      <textarea
        className="w-full h-[32rem] p-3 border rounded-md font-mono text-sm mb-4 resize-none"
        placeholder="Paste or type your JSON scenario here..."
        value={scenarioData}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Scenario JSON data"
      />

      <div className="flex justify-between gap-2">
        <Button onClick={onStart} variant="destructive" className="w-32">
          Start Scenario
        </Button>
      </div>
    </div>
  );
}
