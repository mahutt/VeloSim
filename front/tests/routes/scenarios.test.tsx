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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import ScenarioEditor from '~/routes/scenarios';
import { log } from '~/lib/logger';
import api from '~/api';
import type { ScenarioListResponse } from '~/types';

// Mock the API
vi.mock('~/api');

const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock the error hook
const mockDisplayError = vi.fn();
vi.mock('~/hooks/use-error', () => ({
  default: () => ({ displayError: mockDisplayError }),
}));

const mockScenarios = [
  {
    id: 1,
    name: 'Test Scenario 1',
    user_id: 1,
    content: { stations: [], resources: [] },
    date_created: '2025-01-15T08:30:00Z',
    date_updated: '2025-01-15T08:30:00Z',
  },
  {
    id: 2,
    name: 'Test Scenario 2',
    user_id: 1,
    content: { stations: [], resources: [] },
    date_created: '2025-01-16T10:15:00Z',
    date_updated: '2025-01-16T14:22:00Z',
  },
];

describe('ScenarioEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDisplayError.mockClear();

    // Mock API response for scenarios
    vi.mocked(api.get).mockResolvedValue({
      data: {
        scenarios: mockScenarios,
        total: mockScenarios.length,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    } as { data: ScenarioListResponse });
  });

  it('renders the scenario editor page', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Scenario name')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('Paste or type your JSON scenario here...')
    ).toBeInTheDocument();
  });

  it('loads saved scenarios on mount', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/scenarios')
      );
    });
  });

  it('displays saved scenarios in sidebar', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      expect(screen.getByText('Test Scenario 2')).toBeInTheDocument();
    });
  });

  it('updates scenario name when input changes', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'New Scenario' } });

    expect(nameInput).toHaveValue('New Scenario');
  });

  it('updates scenario content when textarea changes', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

    expect(textarea).toHaveValue('{"test": "data"}');
  });

  it('clears form when New button is clicked', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const nameInput = screen.getByPlaceholderText('Scenario name');
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );

    fireEvent.change(nameInput, { target: { value: 'Test Name' } });
    fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

    const newButton = screen.getByText('New');
    fireEvent.click(newButton);

    expect(nameInput).toHaveValue('');
    expect(textarea).toHaveValue('');
  });

  it('loads selected scenario into editor', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    const scenario1 = screen.getByText('Test Scenario 1');
    fireEvent.click(scenario1);

    const nameInput = screen.getByPlaceholderText('Scenario name');
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );

    expect(nameInput).toHaveValue('Test Scenario 1');
    expect(textarea).toHaveValue(
      JSON.stringify(mockScenarios[0].content, null, 2)
    );
  });

  it('shows alert when Save button is clicked', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Set a scenario name so save doesn't prompt for name
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test Scenario' } });

    // Add valid content so validation passes
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({
          stations: [{ id: 's1' }],
        }),
      },
    });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    expect(alertSpy).toHaveBeenCalledWith(
      'Save Scenario - TODO: Implement backend integration'
    );
    alertSpy.mockRestore();
  });

  it('triggers download when Export button is clicked with valid content and no name', () => {
    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Add some valid scenario content to export
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({
          scenario_title: 'Test Scenario',
          stations: [{ id: 's1', name: 'Station 1' }],
        }),
      },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Should open the name dialog since no name is set
    expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    expect(mockDisplayError).not.toHaveBeenCalled();

    // Enter a name and confirm
    const nameInput = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(nameInput, { target: { value: 'My Export' } });

    const confirmButton = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(confirmButton);

    // Verify blob was created and cleaned up
    expect(log).toHaveBeenCalled();
  });

  it('shows alert when Import button is clicked', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const importButton = screen.getByText('Import');
    fireEvent.click(importButton);

    expect(alertSpy).toHaveBeenCalledWith(
      'Import Scenario - TODO: Implement import functionality'
    );
    alertSpy.mockRestore();
  });

  it('navigates to simulation when Start Simulation is clicked', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const startButton = screen.getByText('Start Simulation');
    fireEvent.click(startButton);

    expect(mockNavigate).toHaveBeenCalledWith('/simulation');
  });

  it('loads scenario content from backend when selected', async () => {
    const testScenario = {
      id: 3,
      name: 'Backend Scenario',
      user_id: 1,
      content: { stations: [{ id: 1, name: 'Station 1' }], resources: [] },
      date_created: '2025-01-17T09:00:00Z',
      date_updated: '2025-01-17T09:00:00Z',
    };

    vi.mocked(api.get).mockResolvedValue({
      data: {
        scenarios: [testScenario],
        total: 1,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    } as { data: ScenarioListResponse });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Backend Scenario')).toBeInTheDocument();
    });

    const scenarioItem = screen.getByText('Backend Scenario');
    fireEvent.click(scenarioItem);

    // Content should be stringified and displayed in textarea
    const textarea = screen.getByLabelText('Scenario JSON data');
    await waitFor(() => {
      expect(textarea).toHaveValue(
        JSON.stringify(testScenario.content, null, 2)
      );
    });
  });

  it('shows error when trying to export empty content', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Set scenario name so validation runs immediately
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Should call displayError since content is empty
    expect(mockDisplayError).toHaveBeenCalledWith(
      'No content to process',
      'Please enter or load a scenario first.'
    );
  });

  it('shows error when trying to export invalid JSON', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Set scenario name so validation runs immediately
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    // Add invalid JSON content
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{invalid json content}' },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Should call displayError since JSON is invalid
    expect(mockDisplayError).toHaveBeenCalledWith(
      'Invalid JSON format',
      'The scenario content is not valid JSON. Please fix the formatting.'
    );
  });

  it('exports with scenario name when name is provided', () => {
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Set scenario name
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'My Test Scenario' } });

    // Add content - use valid scenario structure
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({
          scenario_title: 'Test',
          stations: [{ id: 's1' }],
        }),
      },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Should export directly without showing dialog since name is provided
    expect(
      screen.queryByText('Scenario Name Required')
    ).not.toBeInTheDocument();
    expect(mockDisplayError).not.toHaveBeenCalled();
    expect(log).toHaveBeenCalled();
  });

  it('shows error when exporting scenario with validation errors', () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Set scenario name to avoid name dialog
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    // Add scenario with validation errors
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({
          start_time: 'invalid-time',
          end_time: '25:00',
        }),
      },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Should show validation error
    expect(mockDisplayError).toHaveBeenCalledWith(
      'Scenario validation failed',
      expect.stringContaining('Errors:')
    );
  });

  it('exports valid scenario with warnings', () => {
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
    const consoleWarnSpy = vi
      .spyOn(console, 'warn')
      .mockImplementation(() => {});

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Add scenario with warnings but no errors
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({
          stations: [],
        }),
      },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Dialog should open since no name is set (warnings don't block export)
    expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    expect(mockDisplayError).not.toHaveBeenCalled();

    // Enter a name and confirm export
    const nameInput = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(nameInput, { target: { value: 'Warning Test' } });

    const confirmButton = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(confirmButton);

    // Warning should have been logged when export was confirmed
    expect(consoleWarnSpy).toHaveBeenCalled();

    // Should still export
    expect(log).toHaveBeenCalled();

    consoleWarnSpy.mockRestore();
  });

  it('does not export when user cancels the export dialog', () => {
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    // Add valid content
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify({
          scenario_title: 'Test',
          stations: [{ id: 's1' }],
        }),
      },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    // Dialog should open
    expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();

    // Cancel the export
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    // No download should happen
    expect(global.URL.createObjectURL).not.toHaveBeenCalled();
    expect(global.URL.revokeObjectURL).not.toHaveBeenCalled();
  });
});
