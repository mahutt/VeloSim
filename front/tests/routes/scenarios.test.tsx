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
import type { ScenarioListResponse } from '~/types';
import api from '~/api';
import { toast } from 'sonner';

// Mock Sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock the API module
vi.mock('~/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

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

    // Mock successful validation by default
    vi.mocked(api.post).mockResolvedValue({
      data: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });
  });

  it('renders the scenario editor page', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

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

  it('updates scenario name when input changes', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'New Scenario' } });

    expect(nameInput).toHaveValue('New Scenario');
  });

  it('updates scenario content when textarea changes', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

    expect(textarea).toHaveValue('{"test": "data"}');
  });

  it('clears form when New button is clicked', async () => {
    // Mock the template endpoint
    vi.mocked(api.get).mockImplementation((url) => {
      if (url === '/scenarios/template') {
        return Promise.resolve({ data: {} });
      }
      return Promise.resolve({
        data: {
          scenarios: mockScenarios,
          total: mockScenarios.length,
          page: 1,
          per_page: 10,
          total_pages: 1,
        },
      });
    });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText('Scenario name');
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );

    fireEvent.change(nameInput, { target: { value: 'Test Name' } });
    fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

    const newButton = screen.getByText('New');
    fireEvent.click(newButton);

    await waitFor(() => {
      expect(nameInput).toHaveValue('');
    });
  });

  it('loads selected scenario into editor and shows Edit button', async () => {
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

    await waitFor(() => {
      const nameInput = screen.getByPlaceholderText('Scenario name');
      expect(nameInput).toHaveValue('Test Scenario 1');
      expect(nameInput).toBeDisabled();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    expect(textarea).toBeDisabled();

    // Should show Edit button instead of Save
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.queryByText('Save')).not.toBeInTheDocument();
  });

  it('enables editing when Edit button is clicked', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    // Load a scenario
    const scenario1 = screen.getByText('Test Scenario 1');
    fireEvent.click(scenario1);

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    // Click Edit button
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);

    // Fields should now be enabled
    const nameInput = screen.getByPlaceholderText('Scenario name');
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );

    expect(nameInput).not.toBeDisabled();
    expect(textarea).not.toBeDisabled();

    // Should show Save button instead of Edit
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.queryByText('Edit')).not.toBeInTheDocument();
  });

  it('shows overwrite dialog when saving edited loaded scenario', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    // Load a scenario
    const scenario1 = screen.getByText('Test Scenario 1');
    fireEvent.click(scenario1);

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    // Enter edit mode
    const editButton = screen.getByText('Edit');
    fireEvent.click(editButton);

    // Make a change
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": [{"id": "new"}]}' },
    });

    // Click Save
    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    // Should show overwrite dialog
    await waitFor(() => {
      expect(screen.getByText('Overwrite or Save As New?')).toBeInTheDocument();
    });
  });

  it('overwrites scenario when Overwrite is clicked', async () => {
    // Mock validation success
    vi.mocked(api.post).mockResolvedValue({
      data: { valid: true, errors: [], warnings: [] },
    });

    // Mock PUT success
    vi.mocked(api.put).mockResolvedValue({ data: { id: 1 } });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    // Load, edit, and save
    fireEvent.click(screen.getByText('Test Scenario 1'));

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Edit'));

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": [{"id": "new"}]}' },
    });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(screen.getByText('Overwrite')).toBeInTheDocument();
    });

    // Click Overwrite
    fireEvent.click(screen.getByText('Overwrite'));

    await waitFor(() => {
      expect(api.put).toHaveBeenCalledWith(
        '/scenarios/1',
        expect.objectContaining({
          name: 'Test Scenario 1',
          content: { stations: [{ id: 'new' }] },
        })
      );
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario overwritten successfully!'
      );
    });
  });

  it('saves as new scenario with incremented name when Save As New is clicked', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    // Load, edit, and save
    fireEvent.click(screen.getByText('Test Scenario 1'));

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Edit'));

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": [{"id": "new"}]}' },
    });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(screen.getByText('Save As New')).toBeInTheDocument();
    });

    // Clear all previous mock calls
    vi.mocked(api.post).mockClear();
    vi.mocked(api.get).mockClear();

    // Mock validation for the save
    vi.mocked(api.post).mockResolvedValueOnce({
      data: { valid: true, errors: [], warnings: [] },
    });

    // Mock the actual save call
    vi.mocked(api.post).mockResolvedValueOnce({ data: { id: 3 } });

    // Mock the refresh call after save
    vi.mocked(api.get).mockResolvedValue({
      data: {
        scenarios: mockScenarios,
        total: mockScenarios.length,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    });

    // Click Save As New
    fireEvent.click(screen.getByText('Save As New'));

    await waitFor(() => {
      // Find the POST call to /scenarios (not /scenarios/validate)
      const saveCalls = vi
        .mocked(api.post)
        .mock.calls.filter((call) => call[0] === '/scenarios');

      expect(saveCalls.length).toBeGreaterThan(0);
      expect(saveCalls[0][1]).toMatchObject({
        name: 'Test Scenario 1 (1)', // Should be incremented with parentheses
        content: { stations: [{ id: 'new' }] },
        allow_duplicate_name: false,
      });
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });
  });

  it('navigates to simulation when Start Simulation is clicked', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const startButton = screen.getByText('Start Simulation');
    fireEvent.click(startButton);

    expect(mockNavigate).toHaveBeenCalledWith('/simulation');
  });

  it('shows error when trying to export empty content', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'No content to process',
        'Please enter or load a scenario first.'
      );
    });
  });

  it('shows error when trying to export invalid JSON', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{invalid json content}' },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Invalid JSON format',
        'The scenario content is not valid JSON. Please fix the formatting.'
      );
    });
  });

  it('handles API error when loading scenarios fails', async () => {
    // Mock API to fail
    vi.mocked(api.get).mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Failure loading scenarios',
        'All scenarios failed to load.',
        expect.any(Function)
      );
    });
  });

  it('handles partial failure when loading scenarios', async () => {
    // Mock first page success, second page failure
    vi.mocked(api.get)
      .mockResolvedValueOnce({
        data: {
          scenarios: [mockScenarios[0]],
          total: 20,
          page: 1,
          per_page: 10,
          total_pages: 2,
        },
      })
      .mockRejectedValueOnce(new Error('Network error'));

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Failure loading scenarios',
        'Some scenarios may be missing from the list.',
        undefined
      );
    });
  });

  it('handles save scenario with name update', async () => {
    // Mock validation and save
    vi.mocked(api.post)
      .mockResolvedValueOnce({
        data: { valid: true, errors: [], warnings: [] },
      })
      .mockResolvedValueOnce({
        data: { id: 5 },
      });

    // Mock refresh call
    vi.mocked(api.get).mockResolvedValue({
      data: {
        scenarios: mockScenarios,
        total: mockScenarios.length,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    // Add content and name
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'New Test Scenario' } });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);
  });

  it('handles save scenario without returning ID', async () => {
    // Mock validation and save without ID
    vi.mocked(api.post)
      .mockResolvedValueOnce({
        data: { valid: true, errors: [], warnings: [] },
      })
      .mockResolvedValueOnce({
        data: {},
      });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'Test' } });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);
  });

  it('syncs scenario_title with scenarioName when content changes', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );

    // Add content with scenario_title
    fireEvent.change(textarea, {
      target: { value: '{"scenario_title": "Auto Title", "stations": []}' },
    });

    await waitFor(() => {
      const nameInput = screen.getByPlaceholderText('Scenario name');
      expect(nameInput).toHaveValue('Auto Title');
    });
  });

  it('updates scenario_title when name changes', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    // First add some content
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    // Then change the name
    const nameInput = screen.getByPlaceholderText('Scenario name');
    fireEvent.change(nameInput, { target: { value: 'New Name' } });

    // Check that scenario_title in JSON is updated
    await waitFor(() => {
      const content = JSON.parse((textarea as HTMLTextAreaElement).value);
      expect(content.scenario_title).toBe('New Name');
    });
  });

  it('handles template fetch failure when clicking New', async () => {
    // Mock template endpoint to fail
    vi.mocked(api.get).mockImplementation((url) => {
      if (url === '/scenarios/template') {
        return Promise.reject(new Error('Template not found'));
      }
      return Promise.resolve({
        data: {
          scenarios: mockScenarios,
          total: mockScenarios.length,
          page: 1,
          per_page: 10,
          total_pages: 1,
        },
      });
    });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const newButton = screen.getByText('New');
    fireEvent.click(newButton);

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      expect(textarea).toHaveValue('');
    });
  });

  it('handles overwrite without returning ID', async () => {
    // Mock validation success
    vi.mocked(api.post).mockResolvedValue({
      data: { valid: true, errors: [], warnings: [] },
    });

    // Mock PUT success without id
    vi.mocked(api.put).mockResolvedValue({ data: {} });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    // Load, edit, and save
    fireEvent.click(screen.getByText('Test Scenario 1'));

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Edit'));

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": [{"id": "new"}]}' },
    });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(screen.getByText('Overwrite')).toBeInTheDocument();
    });

    // Click Overwrite
    fireEvent.click(screen.getByText('Overwrite'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario overwritten successfully!'
      );
    });
  });

  it('handles save as new without returning ID', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
    });

    // Load, edit, and save
    fireEvent.click(screen.getByText('Test Scenario 1'));

    await waitFor(() => {
      expect(screen.getByText('Edit')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Edit'));

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": [{"id": "new"}]}' },
    });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => {
      expect(screen.getByText('Save As New')).toBeInTheDocument();
    });

    // Clear and mock for save as new without ID
    vi.mocked(api.post).mockClear();
    vi.mocked(api.get).mockClear();

    vi.mocked(api.post)
      .mockResolvedValueOnce({
        data: { valid: true, errors: [], warnings: [] },
      })
      .mockResolvedValueOnce({
        data: {}, // No ID
      });

    vi.mocked(api.get).mockResolvedValue({
      data: {
        scenarios: mockScenarios,
        total: mockScenarios.length,
        page: 1,
        per_page: 10,
        total_pages: 1,
      },
    });

    fireEvent.click(screen.getByText('Save As New'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });
  });

  it('opens name dialog when exporting without name', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    });
  });

  it('opens name dialog when saving without name', async () => {
    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    });
  });

  it('handles name dialog confirmation for export', async () => {
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    const exportButton = screen.getByText('Export');
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    });

    // Enter name and confirm
    const dialogInput = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(dialogInput, { target: { value: 'Export Test' } });

    const confirmButton = screen.getByText('Continue');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  it('handles name dialog confirmation for save', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({
        data: { valid: true, errors: [], warnings: [] },
      })
      .mockResolvedValueOnce({
        data: { id: 10 },
      });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"stations": []}' },
    });

    const saveButton = screen.getByText('Save');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    });

    // Enter name and confirm
    const dialogInput = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(dialogInput, { target: { value: 'Save Test' } });

    const confirmButton = screen.getByText('Continue');
    fireEvent.click(confirmButton);
  });
});
