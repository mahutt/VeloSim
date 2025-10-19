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
import * as scenarioUtils from '~/lib/scenario-utils';

// Mock the scenario utils module
vi.mock('~/lib/scenario-utils', () => ({
  loadSavedScenarios: vi.fn(),
  getScenarioPreview: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockScenarios = [
  {
    id: 1,
    name: 'Test Scenario 1',
    user_id: 1,
    content: '{"stations": []}',
    date_created: '2025-01-15T08:30:00Z',
    date_updated: '2025-01-15T08:30:00Z',
  },
  {
    id: 2,
    name: 'Test Scenario 2',
    user_id: 1,
    content: '{"stations": [], "resources": []}',
    date_created: '2025-01-16T10:15:00Z',
    date_updated: '2025-01-16T14:22:00Z',
  },
];

describe('ScenarioEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(scenarioUtils.loadSavedScenarios).mockResolvedValue(
      mockScenarios
    );
    vi.mocked(scenarioUtils.getScenarioPreview).mockReturnValue('2 properties');
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
      expect(scenarioUtils.loadSavedScenarios).toHaveBeenCalled();
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
      JSON.stringify(JSON.parse(mockScenarios[0].content), null, 2)
    );
  });

  it('shows alert when Save button is clicked', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    expect(alertSpy).toHaveBeenCalledWith(
      'Save Scenario - TODO: Implement backend integration'
    );
    alertSpy.mockRestore();
  });

  it('shows alert when Export button is clicked', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    expect(alertSpy).toHaveBeenCalledWith(
      'Export Scenario - TODO: Implement export functionality'
    );
    alertSpy.mockRestore();
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

  it('displays error when invalid JSON scenario is selected', async () => {
    const invalidScenario = {
      id: 3,
      name: 'Invalid Scenario',
      user_id: 1,
      content: 'invalid json',
      date_created: '2025-01-17T09:00:00Z',
      date_updated: '2025-01-17T09:00:00Z',
    };

    vi.mocked(scenarioUtils.loadSavedScenarios).mockResolvedValue([
      invalidScenario,
    ]);

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Invalid Scenario')).toBeInTheDocument();
    });

    const invalidScenarioItem = screen.getByText('Invalid Scenario');
    fireEvent.click(invalidScenarioItem);

    expect(screen.getByText('Unable to load scenario.')).toBeInTheDocument();
  });
});
