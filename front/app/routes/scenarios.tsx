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

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router';
import type { Scenario, ScenarioListResponse } from '~/types';
import ScenarioToolbar from '~/components/scenario/scenario-toolbar';
import ScenarioTextArea from '~/components/scenario/scenario-textarea';
import ScenarioSidebar from '~/components/scenario/scenario-sidebar';
import ScenarioNameDialog from '~/components/scenario/scenario-name-dialog';
import OverwriteSaveDialog from '~/components/scenario/overwrite-save-dialog';
import { useScenarioOperations } from '~/hooks/use-scenario-operations';
import useError from '~/hooks/use-error';
import api from '~/api';

export default function ScenarioEditor() {
  // Refs
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // State
  const [scenarioContent, setScenarioContent] = useState('');
  const [scenarioName, setScenarioName] = useState('');
  const [scenarioDescription, setScenarioDescription] = useState('');
  const [savedScenarios, setSavedScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(
    null
  );
  const [isEditMode, setIsEditMode] = useState(false);
  const [nameDialogOpen, setNameDialogOpen] = useState(false);
  const [overwriteDialogOpen, setOverwriteDialogOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<'export' | 'save' | null>(
    null
  );

  // Hooks
  const navigate = useNavigate();
  const { displayError } = useError();
  const {
    validateContent,
    exportScenario,
    saveScenario,
    overwriteScenario,
    deleteScenario,
  } = useScenarioOperations();

  /**
   * Load all saved scenarios for the current user
   * Fetches paginated data and returns all scenarios
   */
  const loadSavedScenarios = useCallback(async (): Promise<Scenario[]> => {
    const scenarios: Scenario[] = [];
    let page = 1;
    const perPage = 10;
    let totalPages = 1;
    let failureOccurred = false;

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
        failureOccurred = true;
        break;
      }
    }

    if (failureOccurred) {
      displayError(
        'Failure loading scenarios',
        scenarios.length > 0
          ? 'Some scenarios may be missing from the list.'
          : 'All scenarios failed to load.',
        scenarios.length > 0 ? undefined : loadSavedScenarios
      );
    }
    return scenarios;
  }, [displayError]);

  // Load scenarios on mount only
  useEffect(() => {
    loadSavedScenarios().then(setSavedScenarios);
  }, []); // Only run once on mount

  // Sync scenarioName with scenario_title in JSON content
  useEffect(() => {
    if (!scenarioContent) return;
    try {
      const parsed = JSON.parse(scenarioContent);
      if (parsed.scenario_title && parsed.scenario_title !== scenarioName) {
        setScenarioName(parsed.scenario_title);
      }
    } catch {
      // ignore if not valid JSON
    }
  }, [scenarioContent, scenarioName]);

  // Helper function to generate incremented name
  const generateIncrementedName = useCallback(
    (baseName: string, scenarios: Scenario[]): string => {
      const existingNames = scenarios.map((s) => s.name);

      // Match a name ending with optional space and (number), e.g., "Test (2)"
      const match = baseName.match(/^(.*?)(?:\s*\((\d+)\))?$/);
      let nameWithoutNumber = baseName;
      let startCounter = 1;

      if (match) {
        nameWithoutNumber = match[1].trim();
        if (match[2]) {
          startCounter = parseInt(match[2], 10) + 1;
        }
      }

      let counter = startCounter;
      let newName = `${nameWithoutNumber} (${counter})`;

      while (existingNames.includes(newName)) {
        counter++;
        newName = `${nameWithoutNumber} (${counter})`;
      }

      return newName;
    },
    []
  );

  // Import scenario handler
  const handleImportScenario = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
      const file = event.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const text = e.target?.result as string;
          const parsed = JSON.parse(text);
          const contentToSave = JSON.stringify(parsed, null, 2);

          const fileName = file.name.replace(/\.[^/.]+$/, '');
          const name = fileName || 'Imported Scenario';

          setScenarioContent(contentToSave);
          setScenarioName(name);
          setScenarioDescription(parsed.description || '');

          // Save to backend - backend will validate
          const newId = await saveScenario(
            contentToSave,
            name,
            parsed.description || ''
          );

          if (newId) {
            setSelectedScenarioId(newId);
            // Refresh sidebar after successful import
            const scenarios = await loadSavedScenarios();
            setSavedScenarios(scenarios);
          }
        } catch {
          displayError(
            'Import Failed',
            'The file is not a valid JSON scenario.'
          );
        }
      };
      reader.readAsText(file);
      // Reset input value so same file can be imported again if needed
      event.target.value = '';
    },
    [saveScenario, displayError, loadSavedScenarios]
  );

  const handleStartScenario = async () => {
    try {
      // Validate content first
      if (!scenarioContent.trim()) {
        displayError(
          'No Scenario',
          'Please create or load a scenario before starting simulation.'
        );
        return;
      }

      // Parse the scenario content
      let content;
      try {
        content = JSON.parse(scenarioContent);
      } catch {
        displayError(
          'Invalid Scenario',
          'The scenario content is not valid JSON. Please fix it before starting.'
        );
        return;
      }

      // Wrap scenario content in the expected format
      const scenarioData = {
        id: selectedScenarioId || 0, // Use 0 for unsaved scenarios
        name: scenarioName || 'Untitled Scenario',
        content: content,
      };

      // Call backend API to initialize simulation with scenario data
      const response = await api.post('/simulation/initialize', scenarioData);
      const data = response.data;

      if (data && data.sim_id) {
        const simId = data.sim_id;
        console.log('Received sim_id:', simId);
        // Navigate to simulation page with sim_id
        navigate(`/simulation/${simId}`);
      } else {
        throw new Error('No sim_id received from server');
      }
    } catch (error) {
      console.error('Error starting simulation:', error);
      displayError(
        'Initialization Failed',
        'Failed to initialize simulation. Please try again.'
      );
    }
  };

  const handleSaveScenario = useCallback(async () => {
    // Sync scenario_title with scenarioName
    let contentToSave = scenarioContent;
    try {
      if (scenarioContent) {
        const parsed = JSON.parse(scenarioContent);
        parsed.scenario_title = scenarioName;
        contentToSave = JSON.stringify(parsed, null, 2);
      }
    } catch {
      // If not valid JSON, saveScenario will handle the error
    }

    // If editing an existing scenario, show Overwrite/Save As New dialog
    if (isEditMode && selectedScenarioId) {
      setOverwriteDialogOpen(true);
      return;
    }

    // Check if scenario has a name
    if (!scenarioName.trim()) {
      setPendingAction('save');
      setNameDialogOpen(true);
    } else {
      const newId = await saveScenario(
        contentToSave,
        scenarioName,
        scenarioDescription
      );
      if (newId) setSelectedScenarioId(newId);
      // Refresh sidebar after save
      const scenarios = await loadSavedScenarios();
      setSavedScenarios(scenarios);
    }
  }, [
    scenarioContent,
    scenarioName,
    scenarioDescription,
    isEditMode,
    selectedScenarioId,
    saveScenario,
    loadSavedScenarios,
  ]);

  // Overwrite/Save As New dialog actions
  const handleOverwrite = useCallback(async () => {
    if (selectedScenarioId) {
      const newId = await overwriteScenario(
        selectedScenarioId,
        scenarioContent,
        scenarioName,
        scenarioDescription
      );
      if (newId) setSelectedScenarioId(newId);
      setOverwriteDialogOpen(false);
      setIsEditMode(false);
      // Refresh sidebar after overwrite
      const scenarios = await loadSavedScenarios();
      setSavedScenarios(scenarios);
    }
  }, [
    selectedScenarioId,
    scenarioContent,
    scenarioName,
    scenarioDescription,
    overwriteScenario,
    loadSavedScenarios,
  ]);

  const handleSaveAsNew = useCallback(async () => {
    // Auto-increment the scenario name
    const newName = generateIncrementedName(scenarioName, savedScenarios);
    const newId = await saveScenario(
      scenarioContent,
      newName,
      scenarioDescription
    );
    setScenarioName(newName);
    setOverwriteDialogOpen(false);
    setIsEditMode(false);
    if (newId) setSelectedScenarioId(newId);
    // Refresh sidebar after save as new
    const scenarios = await loadSavedScenarios();
    setSavedScenarios(scenarios);
  }, [
    scenarioName,
    savedScenarios,
    scenarioContent,
    scenarioDescription,
    generateIncrementedName,
    saveScenario,
    loadSavedScenarios,
  ]);

  const handleExportScenario = useCallback(async () => {
    // Validate content first, then check for name
    // This provides faster feedback if content is invalid
    const parsedContent = await validateContent(scenarioContent);

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
  }, [scenarioContent, scenarioName, validateContent, exportScenario]);

  const handleNameDialogConfirm = useCallback(
    async (name: string) => {
      // Update the scenario name
      setScenarioName(name);

      // Perform the pending action
      if (pendingAction === 'export') {
        await exportScenario(scenarioContent, name);
      } else if (pendingAction === 'save') {
        const newId = await saveScenario(
          scenarioContent,
          name,
          scenarioDescription
        );
        if (newId) {
          setSelectedScenarioId(newId);
          // Refresh sidebar after save
          const scenarios = await loadSavedScenarios();
          setSavedScenarios(scenarios);
        }
      }

      // Clear pending action
      setPendingAction(null);
    },
    [
      pendingAction,
      scenarioContent,
      scenarioDescription,
      exportScenario,
      saveScenario,
      loadSavedScenarios,
    ]
  );

  const handleNewScenario = useCallback(() => {
    api
      .get('/scenarios/template')
      .then((response) => {
        const template = response.data;
        // Extract scenario_title and description from template
        let name = '';
        let description = '';
        let content = {};
        if (template.content) {
          // Remove scenario_title from content
          const { scenario_title, ...rest } = template.content;
          name = scenario_title || '';
          content = rest;
        }
        // Use top-level description if present
        if (template.description) {
          description = template.description;
        }
        setScenarioName(name);
        setScenarioDescription(description);
        setScenarioContent(JSON.stringify({ ...content }, null, 2));
      })
      .catch(() => {
        setScenarioContent('');
        setScenarioName('');
        setScenarioDescription('');
      });
    setSelectedScenarioId(null);
    setIsEditMode(false); // Reset edit mode
  }, []);

  const handleSelectScenario = useCallback(
    (scenario: Scenario) => {
      try {
        // Reorder keys for consistent display
        const c = scenario.content;
        const ordered = {
          start_time: c.start_time,
          end_time: c.end_time,
          resources: c.resources,
          stations: c.stations,
          initial_tasks: c.initial_tasks,
          scheduled_tasks: c.scheduled_tasks,
        };
        setScenarioContent(JSON.stringify(ordered, null, 2));
        setScenarioName(scenario.name);
        setScenarioDescription(scenario.description ?? '');
        setSelectedScenarioId(scenario.id);
        setIsEditMode(false);
      } catch {
        displayError(
          'Unable to load scenario',
          'The scenario could not be parsed as JSON.'
        );
      }
    },
    [displayError]
  );

  const handleDeleteScenario = useCallback(
    async (scenarioId: number) => {
      const success = await deleteScenario(scenarioId);

      if (success) {
        // If the deleted scenario was selected, clear the editor
        if (selectedScenarioId === scenarioId) {
          setScenarioContent('');
          setScenarioName('');
          setScenarioDescription('');
          setSelectedScenarioId(null);
          setIsEditMode(false);
        }

        // Refresh sidebar
        const scenarios = await loadSavedScenarios();
        setSavedScenarios(scenarios);
      }
    },
    [selectedScenarioId, deleteScenario, loadSavedScenarios]
  );

  return (
    <div className="container mx-auto max-w-6xl py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Scenario Editor</h1>

      {/* Hidden file input for import */}
      <input
        type="file"
        accept="application/json"
        ref={fileInputRef}
        className="hidden"
        onChange={handleImportScenario}
      />

      <ScenarioToolbar
        scenarioName={scenarioName}
        onNameChange={setScenarioName}
        onImport={() => fileInputRef.current?.click()}
        onNew={handleNewScenario}
        isEditMode={isEditMode}
        isExistingScenario={!!selectedScenarioId}
      />

      <div className="flex flex-col lg:flex-row gap-6">
        <ScenarioTextArea
          scenarioData={scenarioContent}
          scenarioDescription={scenarioDescription}
          onDescriptionChange={setScenarioDescription}
          onChange={setScenarioContent}
          onSave={handleSaveScenario}
          onExport={handleExportScenario}
          onStart={handleStartScenario}
          isEditMode={isEditMode}
          isExistingScenario={!!selectedScenarioId}
          onEdit={() => setIsEditMode(true)}
        />

        <ScenarioSidebar
          scenarios={savedScenarios}
          selectedScenarioId={selectedScenarioId}
          onSelect={handleSelectScenario}
          onDelete={handleDeleteScenario}
        />
      </div>

      <ScenarioNameDialog
        open={nameDialogOpen}
        onOpenChange={setNameDialogOpen}
        currentName={scenarioName}
        onConfirm={handleNameDialogConfirm}
      />

      <OverwriteSaveDialog
        open={overwriteDialogOpen}
        onOpenChange={setOverwriteDialogOpen}
        onOverwrite={handleOverwrite}
        onSaveAsNew={handleSaveAsNew}
        scenarioName={scenarioName}
      />
    </div>
  );
}
