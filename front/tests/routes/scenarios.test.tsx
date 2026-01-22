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
    delete: vi.fn(),
  },
}));

const mockNavigate = vi.fn();
const mockBlocker = { state: 'unblocked', proceed: vi.fn(), reset: vi.fn() };
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useBlocker: () => mockBlocker,
  };
});

// Mock the error hook
const mockDisplayError = vi.fn();
vi.mock('~/hooks/use-error', () => ({
  default: () => ({ displayError: mockDisplayError }),
}));

// Mock the logger module
vi.mock('~/lib/logger', () => ({
  log: vi.fn(),
  LogLevel: {
    DEBUG: 'debug',
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error',
  },
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

    // Unsaved changes dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
    });

    // Click Discard to proceed with New
    const discardButton = screen.getByText('Discard');
    fireEvent.click(discardButton);

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
    // Override the default post mock to return sim_id
    vi.mocked(api.post).mockReset();
    vi.mocked(api.post).mockResolvedValue({
      data: {
        sim_id: 'test-sim-123',
      },
    });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Simulation')).toBeInTheDocument();
    });

    // Add valid scenario content
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    const validScenario = JSON.stringify({
      resources: [],
      stations: [],
    });
    fireEvent.change(textarea, { target: { value: validScenario } });

    const startButton = screen.getByText('Start Simulation');
    fireEvent.click(startButton);

    // Wait for navigation
    await waitFor(
      () => {
        expect(mockNavigate).toHaveBeenCalledWith('/simulation/test-sim-123');
      },
      { timeout: 3000 }
    );
  });

  it('shows structured validation errors from initialize', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: {
        data: {
          detail: {
            errors: [
              { field: 'start_time', message: 'is required', line: 5 },
              { message: 'generic issue' },
            ],
          },
        },
      },
    });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Simulation')).toBeInTheDocument();
    });

    // Valid JSON to reach API call
    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"resources": [], "stations": []}' },
    });

    fireEvent.click(screen.getByText('Start Simulation'));

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Initialization Failed',
        expect.stringContaining('[start_time]')
      );
    });

    const message = mockDisplayError.mock.calls.at(-1)?.[1] as string;
    expect(message).toContain('is required');
    expect(message).toContain('line 5');
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('falls back to detail string when initialize fails', async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: { data: { detail: 'custom failure' } },
    });

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Simulation')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"resources": [], "stations": []}' },
    });

    fireEvent.click(screen.getByText('Start Simulation'));

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Initialization Failed',
        'custom failure'
      );
    });
  });

  it('falls back to error.message when initialize throws generic error', async () => {
    vi.mocked(api.post).mockRejectedValueOnce(new Error('boom'));

    render(
      <BrowserRouter>
        <ScenarioEditor />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Simulation')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(
      'Paste or type your JSON scenario here...'
    );
    fireEvent.change(textarea, {
      target: { value: '{"resources": [], "stations": []}' },
    });

    fireEvent.click(screen.getByText('Start Simulation'));

    await waitFor(() => {
      expect(mockDisplayError).toHaveBeenCalledWith(
        'Initialization Failed',
        'boom'
      );
    });
  });

  it('loads scenario content from backend when selected', async () => {
    const testScenario = {
      id: 3,
      name: 'Backend Scenario',
      user_id: 1,
      content: { resources: [], stations: [{ id: 1, name: 'Station 1' }] },
      date_created: '2025-01-17T09:00:00Z',
      date_updated: '2025-01-17T09:00:00Z',
    };

    vi.mocked(api.get).mockResolvedValue({
      data: {
        scenarios: [...mockScenarios, testScenario],
        total: mockScenarios.length + 1,
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
      expect(screen.getByText('Backend Scenario')).toBeInTheDocument();
    });

    const scenarioItem = screen.getByText('Backend Scenario');
    fireEvent.click(scenarioItem);

    // Content should be stringified and displayed in textarea
    const textarea = screen.getByLabelText(
      'Scenario JSON'
    ) as HTMLTextAreaElement;
    await waitFor(() => {
      expect(textarea.value).toContain('Station 1');
    });
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

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });
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

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });
  });

  describe('ScenarioEditor - Delete Functionality', () => {
    it('opens delete confirmation dialog when delete button is clicked', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Find and click the delete button
      const deleteButtons = screen.getAllByLabelText(/Delete Test Scenario/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument();
        expect(
          screen.getByText(/Are you sure you want to delete "Test Scenario 1"/i)
        ).toBeInTheDocument();
      });
    });

    it('deletes scenario and clears editor when confirmed', async () => {
      vi.mocked(api.delete).mockResolvedValueOnce({ data: {} });

      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Select the scenario first
      fireEvent.click(screen.getByText('Test Scenario 1'));

      await waitFor(() => {
        const nameInput = screen.getByPlaceholderText('Scenario name');
        expect(nameInput).toHaveValue('Test Scenario 1');
      });

      // Click delete button
      const deleteButtons = screen.getAllByLabelText(/Delete Test Scenario 1/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete Scenario')).toBeInTheDocument();
      });

      // Confirm deletion - look for the Delete button inside DialogFooter
      const deleteConfirmButton = screen.getByRole('button', {
        name: /^Delete$/i,
      });
      fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(api.delete).toHaveBeenCalledWith('/scenarios/1');
        expect(toast.success).toHaveBeenCalledWith(
          'Scenario deleted successfully!'
        );
      });

      // Editor should be cleared
      await waitFor(() => {
        const nameInput = screen.getByPlaceholderText('Scenario name');
        expect(nameInput).toHaveValue('');
      });
    });

    it('closes dialog when cancel is clicked', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByLabelText(/Delete Test Scenario 1/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument();
      });

      // Click cancel
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelButton);

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByText('Delete')).not.toBeInTheDocument();
      });

      expect(api.delete).not.toHaveBeenCalled();
    });

    it('deletes non-selected scenario without clearing editor', async () => {
      vi.mocked(api.delete).mockResolvedValueOnce({ data: {} });

      // Mock the refresh to return only scenario 1 after deleting scenario 2
      vi.mocked(api.get)
        .mockResolvedValueOnce({
          data: {
            scenarios: mockScenarios,
            total: mockScenarios.length,
            page: 1,
            per_page: 10,
            total_pages: 1,
          },
        })
        .mockResolvedValueOnce({
          data: {
            scenarios: [mockScenarios[0]], // Only scenario 1 remains
            total: 1,
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
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
        expect(screen.getByText('Test Scenario 2')).toBeInTheDocument();
      });

      // Select scenario 1
      fireEvent.click(screen.getByText('Test Scenario 1'));

      await waitFor(() => {
        const nameInput = screen.getByPlaceholderText('Scenario name');
        expect(nameInput).toHaveValue('Test Scenario 1');
      });

      // Delete scenario 2 (not selected) - find it specifically
      const scenario2Card = screen
        .getByText('Test Scenario 2')
        .closest('.group');
      const deleteButton = scenario2Card?.querySelector(
        '[aria-label*="Delete Test Scenario 2"]'
      ) as HTMLElement;

      expect(deleteButton).toBeTruthy();
      fireEvent.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument();
        expect(
          screen.getByText(/Are you sure you want to delete "Test Scenario 2"/i)
        ).toBeInTheDocument();
      });

      const deleteConfirmButton = screen.getByRole('button', {
        name: /^Delete$/i,
      });
      fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(api.delete).toHaveBeenCalledWith('/scenarios/2');
        expect(toast.success).toHaveBeenCalledWith(
          'Scenario deleted successfully!'
        );
      });

      // Scenario 2 should be gone from sidebar
      await waitFor(() => {
        expect(screen.queryByText('Test Scenario 2')).not.toBeInTheDocument();
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });
    });

    it('handles delete API error gracefully', async () => {
      vi.mocked(api.delete).mockRejectedValueOnce({
        response: { data: { detail: 'Cannot delete scenario' } },
      });

      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByLabelText(/Delete Test Scenario 1/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument();
      });

      const deleteConfirmButton = screen.getByRole('button', {
        name: /^Delete$/i,
      });
      fireEvent.click(deleteConfirmButton);

      await waitFor(() => {
        expect(mockDisplayError).toHaveBeenCalledWith(
          'Failed to delete scenario',
          'Cannot delete scenario'
        );
      });
    });

    it('shows scenario name in delete confirmation dialog', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Click delete button for scenario 1
      const deleteButtons = screen.getAllByLabelText(/Delete Test Scenario 1/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete Scenario')).toBeInTheDocument();
        expect(
          screen.getByText(/Are you sure you want to delete "Test Scenario 1"/i)
        ).toBeInTheDocument();
      });

      // Close dialog
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelButton);

      // Click delete for scenario 2
      const deleteButtons2 = screen.getAllByLabelText(
        /Delete Test Scenario 2/i
      );
      fireEvent.click(deleteButtons2[0]);

      await waitFor(() => {
        expect(
          screen.getByText(/Are you sure you want to delete "Test Scenario 2"/i)
        ).toBeInTheDocument();
      });
    });

    it('prevents scenario selection when clicking delete button', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Click delete button (should not select scenario)
      const deleteButtons = screen.getAllByLabelText(/Delete Test Scenario 1/i);
      fireEvent.click(deleteButtons[0]);

      // Dialog should open, but scenario should not be selected
      await waitFor(() => {
        expect(screen.getByText('Delete')).toBeInTheDocument();
      });

      const nameInput = screen.getByPlaceholderText('Scenario name');
      expect(nameInput).toHaveValue(''); // Editor should be empty
    });
  });
  describe('ScenarioEditor - Additional Coverage', () => {
    it('handles invalid JSON content without crashing', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
      });

      // Add invalid JSON
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      fireEvent.change(textarea, { target: { value: 'invalid json' } });

      // Name should remain empty with invalid JSON
      const nameInput = screen.getByPlaceholderText('Scenario name');
      expect(nameInput).toHaveValue('');
    });

    it('handles generateIncrementedName with base name', async () => {
      const scenarioWithNumber = {
        id: 3,
        name: 'Test Scenario 1 (2)',
        user_id: 1,
        content: { stations: [] },
        date_created: '2025-01-17T09:00:00Z',
        date_updated: '2025-01-17T09:00:00Z',
      };

      vi.mocked(api.get).mockResolvedValue({
        data: {
          scenarios: [mockScenarios[0], scenarioWithNumber],
          total: 2,
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
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
        expect(screen.getByText('Test Scenario 1 (2)')).toBeInTheDocument();
      });

      // Load and edit scenario with number
      fireEvent.click(screen.getByText('Test Scenario 1 (2)'));

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

      // Clear mocks
      vi.mocked(api.post).mockClear();
      vi.mocked(api.get).mockClear();

      vi.mocked(api.post)
        .mockResolvedValueOnce({
          data: { valid: true, errors: [], warnings: [] },
        })
        .mockResolvedValueOnce({
          data: { id: 4 },
        });

      vi.mocked(api.get).mockResolvedValue({
        data: {
          scenarios: [mockScenarios[0], scenarioWithNumber],
          total: 2,
          page: 1,
          per_page: 10,
          total_pages: 1,
        },
      });

      fireEvent.click(screen.getByText('Save As New'));

      await waitFor(() => {
        const saveCalls = vi
          .mocked(api.post)
          .mock.calls.filter((call) => call[0] === '/scenarios');

        expect(saveCalls.length).toBeGreaterThan(0);
        expect(saveCalls[0][1]).toMatchObject({
          name: 'Test Scenario 1 (3)', // Should increment to 3
        });
      });
    });

    it('handles import with no file selected', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
      });

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      // Simulate change event with no files
      Object.defineProperty(fileInput, 'files', {
        value: null,
        writable: false,
      });

      fireEvent.change(fileInput);

      // Should not call any APIs
      expect(api.post).not.toHaveBeenCalled();
    });

    it('resets file input value after import', async () => {
      const file = new File(
        [JSON.stringify({ stations: [] })],
        'scenario.json',
        { type: 'application/json' }
      );

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

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      // File input value should be reset
      expect(fileInput.value).toBe('');

      // Wait for save to complete
      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          'Scenario saved successfully!'
        );
      });
    });

    it('handles handleSelectScenario with missing optional fields', async () => {
      const scenarioMinimal = {
        id: 3,
        name: 'Minimal Scenario',
        user_id: 1,
        content: {
          start_time: '08:00',
          end_time: '17:00',
          resources: [],
          stations: [],
        },
        date_created: '2025-01-17T09:00:00Z',
        date_updated: '2025-01-17T09:00:00Z',
      };

      vi.mocked(api.get).mockResolvedValue({
        data: {
          scenarios: [scenarioMinimal],
          total: 1,
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
        expect(screen.getByText('Minimal Scenario')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Minimal Scenario'));

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(
          'Paste or type your JSON scenario here...'
        );
        const content = JSON.parse((textarea as HTMLTextAreaElement).value);
        expect(content.initial_tasks).toBeUndefined();
        expect(content.scheduled_tasks).toBeUndefined();
      });
    });

    it('handles loadSavedScenarios retry functionality', async () => {
      // This tests the retry button in the error dialog
      vi.mocked(api.get).mockRejectedValueOnce(new Error('Network error'));

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

      // The third parameter is the retry function
      const retryFunction = mockDisplayError.mock.calls[0][2];
      expect(typeof retryFunction).toBe('function');
    });
  });

  describe('ScenarioEditor - Edge Cases with Empty States', () => {
    it('handles empty content without crashing', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
      });

      // Name input should be empty when there's no content
      const nameInput = screen.getByPlaceholderText('Scenario name');
      expect(nameInput).toHaveValue('');
    });

    it('handles scenario selection with malformed content', async () => {
      const malformedScenario = {
        id: 3,
        name: 'Malformed',
        user_id: 1,
        content: 'not an object' as unknown as object, // Intentionally wrong type
        date_created: '2025-01-17T09:00:00Z',
        date_updated: '2025-01-17T09:00:00Z',
      };

      vi.mocked(api.get).mockResolvedValue({
        data: {
          scenarios: [malformedScenario],
          total: 1,
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
        expect(screen.getByText('Malformed')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Malformed'));
    });
  });

  describe('ScenarioEditor - Code Coverage for Logging and Sidebar Refresh', () => {
    it('logs and refreshes sidebar when importing scenario returns ID', async () => {
      const file = new File(
        [JSON.stringify({ stations: [], description: 'Imported scenario' })],
        'imported.json',
        { type: 'application/json' }
      );

      vi.mocked(api.post)
        .mockResolvedValueOnce({
          data: { valid: true, errors: [], warnings: [] },
        })
        .mockResolvedValueOnce({
          data: { id: 10 },
        });

      vi.mocked(api.get).mockResolvedValue({
        data: {
          scenarios: [
            ...mockScenarios,
            {
              id: 10,
              name: 'imported',
              user_id: 1,
              content: { stations: [] },
              date_created: '2025-01-17T10:00:00Z',
              date_updated: '2025-01-17T10:00:00Z',
            },
          ],
          total: 3,
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

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;

      Object.defineProperty(fileInput, 'files', {
        value: [file],
        writable: false,
      });

      fireEvent.change(fileInput);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          'Scenario saved successfully!'
        );
      });

      // Verify sidebar refresh occurred - this covers lines 181-182
      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('/scenarios')
        );
      });
    });

    it('refreshes sidebar when save as new returns ID', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Test Scenario 1'));

      await waitFor(() => {
        expect(screen.getByText('Edit')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Edit'));

      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      fireEvent.change(textarea, {
        target: { value: '{"stations": [{"id": "modified"}]}' },
      });

      fireEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(screen.getByText('Save As New')).toBeInTheDocument();
      });

      vi.mocked(api.post).mockClear();
      vi.mocked(api.get).mockClear();

      vi.mocked(api.post)
        .mockResolvedValueOnce({
          data: { valid: true, errors: [], warnings: [] },
        })
        .mockResolvedValueOnce({
          data: { id: 15 },
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

      // Verify sidebar refresh occurred - this covers lines 328-329
      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('/scenarios')
        );
      });
    });
  });

  describe('Unsaved Changes Protection', () => {
    it('shows dialog when trying to select another scenario with unsaved changes', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Make changes to the editor
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

      // Try to select another scenario
      fireEvent.click(screen.getByText('Test Scenario 1'));

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
        expect(
          screen.getByText(/You have unsaved changes/i)
        ).toBeInTheDocument();
      });
    });

    it('loads new scenario when Continue is clicked in unsaved dialog', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Make changes
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

      // Try to select another scenario
      fireEvent.click(screen.getByText('Test Scenario 1'));

      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
      });

      // Click Discard
      fireEvent.click(screen.getByText('Discard'));

      // Scenario should load
      await waitFor(() => {
        expect(screen.queryByText('Unsaved Changes')).not.toBeInTheDocument();
      });
    });

    it('keeps current content when Cancel is clicked in unsaved dialog', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Make changes
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      ) as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

      // Try to select another scenario
      fireEvent.click(screen.getByText('Test Scenario 1'));

      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
      });

      // Click Cancel
      fireEvent.click(screen.getByText('Cancel'));

      // Dialog should close and content should remain
      await waitFor(() => {
        expect(screen.queryByText('Unsaved Changes')).not.toBeInTheDocument();
      });
      expect(textarea.value).toBe('{"test": "data"}');
    });

    it('shows dialog when trying to create new scenario with unsaved changes', async () => {
      vi.mocked(api.get).mockImplementation((url) => {
        if (url === '/scenarios/template') {
          return Promise.resolve({
            data: {
              name: '',
              description: '',
              content: {},
            },
          });
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

      // Make changes
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

      // Click New button
      fireEvent.click(screen.getByText('New'));

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
      });
    });

    it('shows dialog when trying to import with unsaved changes', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Scenario Editor')).toBeInTheDocument();
      });

      // Make changes
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      );
      fireEvent.change(textarea, { target: { value: '{"test": "data"}' } });

      // Click Import button
      fireEvent.click(screen.getByText('Import'));

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByText('Unsaved Changes')).toBeInTheDocument();
      });
    });

    it('does not show dialog when no unsaved changes', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Select scenario without making changes
      fireEvent.click(screen.getByText('Test Scenario 1'));

      // Dialog should not appear
      await waitFor(() => {
        expect(screen.queryByText('Unsaved Changes')).not.toBeInTheDocument();
      });
    });

    it('does not show dialog when clicking on currently active scenario with unsaved changes', async () => {
      render(
        <BrowserRouter>
          <ScenarioEditor />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Test Scenario 1')).toBeInTheDocument();
      });

      // Select a scenario first
      fireEvent.click(screen.getByText('Test Scenario 1'));

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(
          'Paste or type your JSON scenario here...'
        ) as HTMLTextAreaElement;
        expect(textarea.value).toBeTruthy();
      });

      // Make changes to the editor
      const textarea = screen.getByPlaceholderText(
        'Paste or type your JSON scenario here...'
      ) as HTMLTextAreaElement;
      const originalValue = textarea.value;
      fireEvent.change(textarea, {
        target: { value: originalValue + '\n// modified' },
      });

      // Click on the same scenario again
      fireEvent.click(screen.getByText('Test Scenario 1'));

      // Dialog should NOT appear since we're clicking on the currently active scenario
      await waitFor(
        () => {
          expect(screen.queryByText('Unsaved Changes')).not.toBeInTheDocument();
        },
        { timeout: 1000 }
      );
    });
  });
});
