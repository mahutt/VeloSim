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

import { Card, CardContent } from '~/components/ui/card';
import type { Scenario } from '~/types';

interface ScenarioSidebarProps {
  scenarios: Scenario[];
  selectedScenarioId: number | null;
  onSelect: (scenario: Scenario) => void;
}

export default function ScenarioSidebar({
  scenarios,
  selectedScenarioId,
  onSelect,
}: ScenarioSidebarProps) {
  return (
    <div className="w-full lg:w-64">
      <div className="bg-gray-50 border rounded-md p-4 h-[32rem] flex flex-col">
        <h2 className="text-lg font-semibold mb-3">Saved Scenarios</h2>

        <div className="flex-1 overflow-y-auto space-y-2">
          {scenarios.length === 0 && (
            <p className="text-gray-400 italic text-sm">No saved scenarios</p>
          )}

          {scenarios.map((scenario) => {
            const isSelected = selectedScenarioId === scenario.id;

            return (
              <Card
                key={scenario.id}
                onClick={() => onSelect(scenario)}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  isSelected ? 'border-2 border-red-500 bg-red-50' : 'bg-white'
                }`}
              >
                <CardContent className="px-3">
                  <div className="flex flex-col gap-1.5">
                    <div className="text-sm font-semibold truncate">
                      {scenario.name}
                    </div>
                    {scenario.description && (
                      <div className="text-xs text-gray-600 line-clamp-2">
                        {scenario.description}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
