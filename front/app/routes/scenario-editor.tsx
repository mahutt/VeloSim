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
import type { Scenario } from '~/types';
import { loadSavedScenarios } from '~/lib/scenario-utils';
import ScenarioToolbar from '~/components/scenario/scenario-toolbar';
import ScenarioTextArea from '~/components/scenario/scenario-textarea';
import ScenarioSidebar from '~/components/scenario/scenario-sidebar';

export default function ScenarioEditor() {
  const [scenarioContent, setScenarioContent] = useState('');
  const [scenarioName, setScenarioName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [savedScenarios, setSavedScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(
    null
  );

  useEffect(() => {
    // Load mock data for UI testing
    loadSavedScenarios().then(setSavedScenarios);
  }, []);

  // TODO: Implement with backend API call
  const handleStartScenario = () => {
    console.log('Start scenario clicked');
    alert('Start Scenario - TODO: Implement backend integration');
  };

  // TODO: Implement with backend API call
  const handleSaveScenario = () => {
    console.log('Save scenario clicked');
    alert('Save Scenario - TODO: Implement backend integration');
  };

  // TODO: Implement export functionality
  const handleExportScenario = () => {
    console.log('Export scenario clicked');
    alert('Export Scenario - TODO: Implement export functionality');
  };

  const handleNewScenario = () => {
    setScenarioContent('');
    setScenarioName('');
    setError(null);
    setSelectedScenarioId(null);
  };

  // TODO: Implement import functionality
  const handleImportScenario = () => {
    console.log('Import scenario clicked');
    alert('Import Scenario - TODO: Implement import functionality');
  };

  const handleSelectScenario = (scenario: Scenario) => {
    try {
      const parsed = JSON.parse(scenario.content);
      setScenarioContent(JSON.stringify(parsed, null, 2));
      setScenarioName(scenario.name);
      setSelectedScenarioId(scenario.id);
      setError(null);
    } catch {
      setError('Unable to load scenario.');
    }
  };

  return (
    <div className="container mx-auto max-w-6xl py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Scenario Editor</h1>

      <ScenarioToolbar
        scenarioName={scenarioName}
        onNameChange={setScenarioName}
        onImport={handleImportScenario}
        onNew={handleNewScenario}
      />

      <div className="flex flex-col lg:flex-row gap-6">
        <ScenarioTextArea
          scenarioData={scenarioContent}
          error={error}
          onChange={setScenarioContent}
          onSave={handleSaveScenario}
          onExport={handleExportScenario}
          onStart={handleStartScenario}
        />

        <ScenarioSidebar
          scenarios={savedScenarios}
          selectedScenarioId={selectedScenarioId}
          onSelect={handleSelectScenario}
        />
      </div>
    </div>
  );
}
