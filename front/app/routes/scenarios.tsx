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
import { useNavigate } from 'react-router';
import type { Scenario, ScenarioListResponse } from '~/types';
import api from '~/api';
import ScenarioToolbar from '~/components/scenario/scenario-toolbar';
import ScenarioTextArea from '~/components/scenario/scenario-textarea';
import ScenarioSidebar from '~/components/scenario/scenario-sidebar';
import ScenarioNameDialog from '~/components/scenario/scenario-name-dialog';
import { useScenarioOperations } from '~/hooks/use-scenario-operations';
import useError from '~/hooks/use-error';

/**
 * Load all saved scenarios for the current user
 * Fetches paginated data and returns all scenarios
 */
async function loadSavedScenarios(): Promise<Scenario[]> {
  const scenarios: Scenario[] = [];
  let page = 1;
  const perPage = 10;
  let totalPages = 1;

  while (page <= totalPages) {
    try {
      const response = await api.get<ScenarioListResponse>(
        `/scenarios?skip=${(page - 1) * perPage}&limit=${perPage}`
      );
      const data = response.data;
      scenarios.push(...data.scenarios);
      totalPages = data.total_pages;
      page += 1;
    } catch (error) {
      console.error('Failed to fetch scenarios:', error);
      break;
    }
  }

  return scenarios;
}

export default function ScenarioEditor() {
  const [scenarioContent, setScenarioContent] = useState('');
  const [scenarioName, setScenarioName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [savedScenarios, setSavedScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(
    null
  );
  const [nameDialogOpen, setNameDialogOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<'export' | 'save' | null>(
    null
  );
  const navigate = useNavigate();
  const { displayError } = useError();
  const { validateContent, exportScenario, saveScenario, importScenario } =
    useScenarioOperations();

  useEffect(() => {
    // Load scenarios from backend API
    loadSavedScenarios()
      .then(setSavedScenarios)
      .catch(() => {
        displayError(
          'Failed to load scenarios',
          'Unable to fetch your saved scenarios. Please try again later.'
        );
      });
  }, [displayError]);

  // TODO: Implement with backend API call
  const handleStartScenario = () => {
    console.log('Start scenario clicked');
    navigate('/simulation');
  };

  const handleSaveScenario = () => {
    // Validate content first, then check for name
    // This provides faster feedback if content is invalid
    const parsedContent = validateContent(scenarioContent);

    if (!parsedContent) {
      // Validation failed, error already displayed
      return;
    }

    // Check if scenario has a name
    if (!scenarioName.trim()) {
      setPendingAction('save');
      setNameDialogOpen(true);
    } else {
      saveScenario(scenarioContent, scenarioName);
    }
  };

  const handleExportScenario = () => {
    // Validate content first, then check for name
    // This provides faster feedback if content is invalid
    const parsedContent = validateContent(scenarioContent);

    if (!parsedContent) {
      // Validation failed, error already displayed
      return;
    }

    // Check if scenario has a name
    if (!scenarioName.trim()) {
      setPendingAction('export');
      setNameDialogOpen(true);
    } else {
      exportScenario(scenarioContent, scenarioName);
    }
  };

  const handleNameDialogConfirm = (name: string) => {
    // Update the scenario name
    setScenarioName(name);

    // Perform the pending action
    if (pendingAction === 'export') {
      exportScenario(scenarioContent, name);
    } else if (pendingAction === 'save') {
      saveScenario(scenarioContent, name);
    }

    // Clear pending action
    setPendingAction(null);
  };

  const handleNewScenario = () => {
    setScenarioContent('');
    setScenarioName('');
    setError(null);
    setSelectedScenarioId(null);
  };

  const handleSelectScenario = (scenario: Scenario) => {
    try {
      setScenarioContent(JSON.stringify(scenario.content, null, 2));
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
        onImport={importScenario}
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

      <ScenarioNameDialog
        open={nameDialogOpen}
        onOpenChange={setNameDialogOpen}
        currentName={scenarioName}
        onConfirm={handleNameDialogConfirm}
      />
    </div>
  );
}
