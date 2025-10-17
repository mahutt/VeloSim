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

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ScenarioEditor from '~/routes/scenario-editor';
import type { Scenario } from '~/types';
import * as scenarioUtils from '~/lib/scenario-utils';

vi.mock('~/lib/scenario-utils');

const mockScenarios: Scenario[] = [
  {
    id: 1,
    name: 'Test Scenario',
    user_id: 1,
    content: '{"stations": [], "resources": []}',
    date_created: '2025-01-15T08:30:00Z',
    date_updated: '2025-01-15T08:30:00Z',
  },
];

describe('ScenarioEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'alert').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.mocked(scenarioUtils.loadSavedScenarios).mockResolvedValue(
      mockScenarios
    );
  });

  it('renders the page title', () => {
    render(<ScenarioEditor />);
    expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
  });

  it('loads saved scenarios on mount', async () => {
    render(<ScenarioEditor />);

    await waitFor(() => {
      expect(scenarioUtils.loadSavedScenarios).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Test Scenario')).toBeInTheDocument();
    });
  });

  it('renders the toolbar with name input', () => {
    render(<ScenarioEditor />);

    const nameInput = screen.getByPlaceholderText('Scenario name');
    expect(nameInput).toBeInTheDocument();
  });

  it('renders Import and New buttons', () => {
    render(<ScenarioEditor />);

    expect(screen.getByText('Import')).toBeInTheDocument();
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('renders the textarea for scenario content', () => {
    render(<ScenarioEditor />);

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    expect(textarea).toBeInTheDocument();
  });

  it('renders Save, Export, and Start Scenario buttons', () => {
    render(<ScenarioEditor />);

    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Export')).toBeInTheDocument();
    expect(screen.getByText('Start Scenario')).toBeInTheDocument();
  });

  it('updates scenario name when input changes', () => {
    render(<ScenarioEditor />);

    const nameInput = screen.getByPlaceholderText(
      'Scenario name'
    ) as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: 'New Scenario Name' } });

    expect(nameInput.value).toBe('New Scenario Name');
  });

  it('updates scenario content when textarea changes', () => {
    render(<ScenarioEditor />);

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '{"test": "value"}' } });

    expect(textarea.value).toBe('{"test": "value"}');
  });

  it('clears form when New button is clicked', () => {
    render(<ScenarioEditor />);

    const nameInput = screen.getByPlaceholderText(
      'Scenario name'
    ) as HTMLInputElement;
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    ) as HTMLTextAreaElement;

    fireEvent.change(nameInput, { target: { value: 'Test Name' } });
    fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

    const newButton = screen.getByText('New');
    fireEvent.click(newButton);

    expect(nameInput.value).toBe('');
    expect(textarea.value).toBe('');
  });

  it('shows alert when Start Scenario is clicked', () => {
    render(<ScenarioEditor />);

    const startButton = screen.getByText('Start Scenario');
    fireEvent.click(startButton);

    expect(window.alert).toHaveBeenCalledWith(
      'Start Scenario - TODO: Implement backend integration'
    );
  });

  it('shows alert when Save is clicked', () => {
    render(<ScenarioEditor />);

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    expect(window.alert).toHaveBeenCalledWith(
      'Save Scenario - TODO: Implement backend integration'
    );
  });

  it('shows alert when Export is clicked', () => {
    render(<ScenarioEditor />);

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    expect(window.alert).toHaveBeenCalledWith(
      'Export Scenario - TODO: Implement export functionality'
    );
  });

  it('shows alert when Import is clicked', () => {
    render(<ScenarioEditor />);

    const importButton = screen.getByText('Import');
    fireEvent.click(importButton);

    expect(window.alert).toHaveBeenCalledWith(
      'Import Scenario - TODO: Implement import functionality'
    );
  });

  it('loads scenario content when a scenario is selected from sidebar', async () => {
    render(<ScenarioEditor />);

    await waitFor(() => {
      expect(screen.getByText('Test Scenario')).toBeInTheDocument();
    });

    const scenarioCard = screen.getByText('Test Scenario');
    fireEvent.click(scenarioCard);

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    ) as HTMLTextAreaElement;
    await waitFor(() => {
      expect(textarea.value).toContain('stations');
      expect(textarea.value).toContain('resources');
    });

    const nameInput = screen.getByPlaceholderText(
      'Scenario name'
    ) as HTMLInputElement;
    expect(nameInput.value).toBe('Test Scenario');
  });

  it('displays error when selecting scenario with invalid JSON', async () => {
    const invalidScenario: Scenario = {
      id: 2,
      name: 'Invalid Scenario',
      user_id: 1,
      content: 'not valid json',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    };

    vi.mocked(scenarioUtils.loadSavedScenarios).mockResolvedValue([
      invalidScenario,
    ]);

    render(<ScenarioEditor />);

    await waitFor(() => {
      expect(screen.getByText('Invalid Scenario')).toBeInTheDocument();
    });

    const scenarioCard = screen.getByText('Invalid Scenario');
    fireEvent.click(scenarioCard);

    await waitFor(() => {
      expect(screen.getByText('Unable to load scenario.')).toBeInTheDocument();
    });
  });

  it('renders the saved scenarios sidebar', async () => {
    render(<ScenarioEditor />);

    await waitFor(() => {
      expect(screen.getByText('Saved Scenarios')).toBeInTheDocument();
    });
  });

  it('handles empty saved scenarios list', async () => {
    vi.mocked(scenarioUtils.loadSavedScenarios).mockResolvedValue([]);

    render(<ScenarioEditor />);

    await waitFor(() => {
      expect(screen.getByText('No saved scenarios')).toBeInTheDocument();
    });
  });
});
