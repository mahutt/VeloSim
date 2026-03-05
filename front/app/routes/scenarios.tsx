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

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  type DragEvent,
} from 'react';
import { useNavigate, useBlocker } from 'react-router';
import type {
  Scenario,
  ScenarioListResponse,
  InitializeSimulationResponse,
} from '~/types';
import ScenarioToolbar from '~/components/scenario/scenario-toolbar';
import ScenarioTextArea from '~/components/scenario/scenario-textarea';
import ScenarioSidebar from '~/components/scenario/scenario-sidebar';
import ScenarioNameDialog from '~/components/scenario/scenario-name-dialog';
import OverwriteSaveDialog from '~/components/scenario/overwrite-save-dialog';
import UnsavedChangesDialog from '~/components/scenario/unsaved-changes-dialog';
import { useScenarioOperations } from '~/hooks/use-scenario-operations';
import useError from '~/hooks/use-error';
import api from '~/api';
import { log, LogLevel } from '~/lib/logger';
import SimulationNameDialog from '~/components/scenario/simulation-name-dialog';

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
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [initialContent, setInitialContent] = useState('');
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);
  const [showSimulationNameDialog, setShowSimulationNameDialog] =
    useState(false);
  const [startingSimulation, setStartingSimulation] = useState(false);
  const [pendingScenario, setPendingScenario] = useState<Scenario | null>(null);
  const [pendingNewScenario, setPendingNewScenario] = useState(false);
  const [pendingImport, setPendingImport] = useState(false);
  const [pendingImportFile, setPendingImportFile] = useState<File | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  // Hooks
  const navigate = useNavigate();
  const { displayError } = useError();
  const {
    validateContent,
    exportScenario,
    saveScenario,
    overwriteScenario,
    deleteScenario,
    formatBackendError,
  } = useScenarioOperations();

  // Block navigation when there are unsaved changes
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges && currentLocation.pathname !== nextLocation.pathname
  );

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

  // Detect unsaved changes by comparing current content with initial content
  // Treat empty content as "no changes" since there's nothing to save
  useEffect(() => {
    const currentTrimmed = scenarioContent.trim();
    const initialTrimmed = initialContent.trim();

    const hasChanges =
      currentTrimmed !== '' && currentTrimmed !== initialTrimmed;
    setHasUnsavedChanges(hasChanges);
  }, [scenarioContent, initialContent]);

  // Show dialog when navigation is blocked
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setShowUnsavedDialog(true);
    }
  }, [blocker.state]);

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

  /**
   * Process and import scenario file
   * @param file Scenario file (JSON) to import
   * @param source Source of the import ('button' or 'drag')
   */
  const processImportedScenario = useCallback(
    async (file: File, source: 'button' | 'drag'): Promise<void> => {
      log({
        message: 'Scenario import via ' + source,
        level: LogLevel.INFO,
        context:
          source === 'drag' ? 'scenario_import_drag' : 'scenario_import_button',
      });

      try {
        const text = await file.text();
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
          // Clear unsaved changes after successful import
          setInitialContent(contentToSave);
          log({
            message: 'Scenario saved after import',
            level: LogLevel.INFO,
            context: 'scenario_save_imported',
          });
          // Refresh sidebar after successful import
          const scenarios = await loadSavedScenarios();
          setSavedScenarios(scenarios);
        }
      } catch {
        displayError('Import Failed', 'The file is not a valid JSON scenario.');
      } finally {
        setPendingImport(false);
        setPendingImportFile(null);
      }
    },
    [displayError, loadSavedScenarios, saveScenario]
  );

  // Import scenario handler
  const handleImportScenario = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
      const file = event.target.files?.[0];
      if (!file) return;

      await processImportedScenario(file, 'button');
      // Reset input value so same file can be imported again if needed
      event.target.value = '';
    },
    [processImportedScenario]
  );

  const handleImport = useCallback(() => {
    if (hasUnsavedChanges) {
      setPendingImport(true);
      setShowUnsavedDialog(true);
      return;
    }

    fileInputRef.current?.click();
  }, [hasUnsavedChanges]);

  const handleDragOver = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (!event.dataTransfer.types.includes('Files')) return;

      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
      // Only set if not already true
      if (!isDraggingFile) {
        setIsDraggingFile(true);
      }
    },
    [isDraggingFile]
  );

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (!event.dataTransfer.types.includes('Files')) return;

    const relatedTarget = event.relatedTarget as Node | null;
    const isLeavingContainer =
      !relatedTarget || !event.currentTarget.contains(relatedTarget);

    if (isLeavingContainer) {
      event.preventDefault();
      setIsDraggingFile(false);
    }
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (!event.dataTransfer.files?.length) return;

      event.preventDefault();
      setIsDraggingFile(false);

      const file = event.dataTransfer.files[0];

      if (hasUnsavedChanges) {
        setPendingImportFile(file);
        setShowUnsavedDialog(true);
        return;
      }

      processImportedScenario(file, 'drag');
    },
    [hasUnsavedChanges, processImportedScenario]
  );

  const handleStartScenario = async (simulationName: string) => {
    setStartingSimulation(true);
    // Validate content first
    if (!scenarioContent.trim()) {
      displayError(
        'No Scenario',
        'Please create or load a scenario before starting simulation.'
      );
      setStartingSimulation(false);
      return;
    }

    // Parse JSON locally (basic check)
    let parsedContent;
    try {
      parsedContent = JSON.parse(scenarioContent);
    } catch {
      displayError('Invalid Scenario', 'Invalid JSON format');
      setStartingSimulation(false);
      return;
    }

    try {
      const requestBody = {
        name: simulationName,
        content: parsedContent,
      };

      const response = await api.post<InitializeSimulationResponse>(
        '/simulation/initialize',
        requestBody
      );

      navigate(`/simulations/${response.data.sim_id}`);
    } catch (error: unknown) {
      console.error('Error starting simulation:', error);
      displayError('Initialization Failed', formatBackendError(error));
      setStartingSimulation(false);
    }
  };

  const handleSaveScenario = useCallback(async () => {
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
        scenarioContent,
        scenarioName,
        scenarioDescription
      );
      if (newId) {
        setSelectedScenarioId(newId);
        // Clear unsaved changes after successful save
        setInitialContent(scenarioContent);
        log({
          message: 'New scenario saved',
          level: LogLevel.INFO,
          context: 'scenario_save_new',
        });
      }
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
      if (newId) {
        setSelectedScenarioId(newId);
        // Clear unsaved changes after successful overwrite
        setInitialContent(scenarioContent);
      }
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
    if (newId) {
      setSelectedScenarioId(newId);
      // Clear unsaved changes after successful save as new
      setInitialContent(scenarioContent);
      log({
        message: 'Scenario saved as new',
        level: LogLevel.INFO,
        context: 'scenario_save_as_new',
      });
    }
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
          // Clear unsaved changes after successful save
          setInitialContent(scenarioContent);
          log({
            message: 'Scenario saved after name dialog',
            level: LogLevel.INFO,
            context: 'scenario_save_name_dialog',
          });
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

  // Core logic to load new scenario (without unsaved check)
  const loadNewScenario = useCallback(() => {
    api
      .get('/scenarios/template')
      .then((response) => {
        const template = response.data;
        const content = template.content || {};
        const name = template.name || '';
        const description = template.description || '';

        setScenarioName(name);
        setScenarioDescription(description);
        const newContent = JSON.stringify(content, null, 2);
        setScenarioContent(newContent);
        setInitialContent(newContent);
      })
      .catch(() => {
        setScenarioContent('');
        setScenarioName('');
        setScenarioDescription('');
        setInitialContent('');
      });
    setSelectedScenarioId(null);
    setIsEditMode(false);
  }, []);

  const handleNewScenario = useCallback(() => {
    // Check for unsaved changes
    if (hasUnsavedChanges) {
      setPendingNewScenario(true);
      setShowUnsavedDialog(true);
      return;
    }

    loadNewScenario();
  }, [hasUnsavedChanges, loadNewScenario]);

  // Core logic to load a scenario (without unsaved check)
  const loadScenario = useCallback(
    (scenario: Scenario) => {
      try {
        const c = scenario.content;
        const ordered = {
          start_time: c.start_time,
          end_time: c.end_time,
          vehicle_battery_capacity: c.vehicle_battery_capacity,
          drivers: c.drivers,
          vehicles: c.vehicles,
          stations: c.stations,
        };
        const content = JSON.stringify(ordered, null, 2);
        setScenarioContent(content);
        setInitialContent(content);
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

  const handleSelectScenario = useCallback(
    (scenario: Scenario) => {
      if (selectedScenarioId === scenario.id) {
        return;
      }

      if (isDeleteDialogOpen) {
        return;
      }

      // Check for unsaved changes
      if (hasUnsavedChanges) {
        setPendingScenario(scenario);
        setShowUnsavedDialog(true);
        return;
      }

      loadScenario(scenario);
    },
    [selectedScenarioId, hasUnsavedChanges, isDeleteDialogOpen, loadScenario]
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
    <div
      className="container mx-auto max-w-6xl py-8 px-4"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDraggingFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm pointer-events-none">
          <p className="text-2xl font-bold">Drop to import scenario</p>
        </div>
      )}
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
        onImport={handleImport}
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
          onStart={() => setShowSimulationNameDialog(true)}
          isEditMode={isEditMode}
          isExistingScenario={!!selectedScenarioId}
          onEdit={() => setIsEditMode(true)}
        />

        <ScenarioSidebar
          scenarios={savedScenarios}
          selectedScenarioId={selectedScenarioId}
          onSelect={handleSelectScenario}
          onDelete={handleDeleteScenario}
          onDeleteDialogChange={setIsDeleteDialogOpen}
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

      <UnsavedChangesDialog
        open={showUnsavedDialog}
        onOpenChange={(open) => {
          setShowUnsavedDialog(open);
          if (!open) {
            setPendingScenario(null);
            setPendingNewScenario(false);
            setPendingImport(false);
            setPendingImportFile(null);
            blocker.reset?.();
          }
        }}
        onCancel={() => {
          log({
            message: 'Loss of unsaved changes prevented',
            level: LogLevel.INFO,
            context: 'unsaved_scenario_changes_preserved',
          });
          setShowUnsavedDialog(false);
          setPendingScenario(null);
          setPendingNewScenario(false);
          setPendingImport(false);
          setPendingImportFile(null);
          blocker.reset?.();
        }}
        onLeave={() => {
          log({
            message: 'Unsaved changes explicitly discarded',
            level: LogLevel.INFO,
            context: 'unsaved_scenario_changes_discarded',
          });
          setShowUnsavedDialog(false);
          if (pendingScenario) {
            loadScenario(pendingScenario);
            setPendingScenario(null);
          } else if (pendingNewScenario) {
            loadNewScenario();
            setPendingNewScenario(false);
          } else if (pendingImportFile) {
            processImportedScenario(pendingImportFile, 'drag');
            setPendingImportFile(null);
          } else if (pendingImport) {
            fileInputRef.current?.click();
            setPendingImport(false);
          } else {
            blocker.proceed?.();
          }
        }}
      />

      <SimulationNameDialog
        open={showSimulationNameDialog}
        onOpenChange={setShowSimulationNameDialog}
        scenarioName={scenarioName}
        onStartSimulation={handleStartScenario}
        startingSimulation={startingSimulation}
      />
    </div>
  );
}
