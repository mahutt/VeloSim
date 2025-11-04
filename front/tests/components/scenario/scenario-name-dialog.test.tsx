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
import { render, screen, fireEvent } from '@testing-library/react';
import ScenarioNameDialog from '~/components/scenario/scenario-name-dialog';

describe('ScenarioNameDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnConfirm = vi.fn();

  beforeEach(() => {
    mockOnOpenChange.mockClear();
    mockOnConfirm.mockClear();
  });

  it('renders when open', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    expect(screen.getByText('Scenario Name Required')).toBeInTheDocument();
    expect(screen.getByLabelText('Scenario Name')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('Enter scenario name')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /continue/i })
    ).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <ScenarioNameDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    expect(
      screen.queryByText('Scenario Name Required')
    ).not.toBeInTheDocument();
  });

  it('displays current name in input', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName="My Scenario"
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    expect(input).toHaveValue('My Scenario');
  });

  it('allows editing the scenario name', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(input, { target: { value: 'New Scenario Name' } });

    expect(input).toHaveValue('New Scenario Name');
  });

  it('calls onConfirm with name when Continue button is clicked', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(input, { target: { value: 'Test Name' } });

    const continueButton = screen.getByRole('button', { name: /continue/i });
    fireEvent.click(continueButton);

    expect(mockOnConfirm).toHaveBeenCalledWith('Test Name');
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('disables Continue button when name is empty', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const continueButton = screen.getByRole('button', { name: /continue/i });
    expect(continueButton).toBeDisabled();
  });

  it('disables Continue button when name is only whitespace', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName="   "
        onConfirm={mockOnConfirm}
      />
    );

    const continueButton = screen.getByRole('button', { name: /continue/i });
    expect(continueButton).toBeDisabled();
  });

  it('enables Continue button when name is provided', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName="Valid Name"
        onConfirm={mockOnConfirm}
      />
    );

    const continueButton = screen.getByRole('button', { name: /continue/i });
    expect(continueButton).toBeEnabled();
  });

  it('closes dialog when Cancel button is clicked', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnConfirm).not.toHaveBeenCalled();
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('confirms when Enter key is pressed in input with valid name', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(input, { target: { value: 'Enter Test' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnConfirm).toHaveBeenCalledWith('Enter Test');
  });

  it('does not confirm when Enter key is pressed with empty name', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  it('closes when Escape key is pressed in input', () => {
    render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(mockOnConfirm).not.toHaveBeenCalled();
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('resets name to current when dialog reopens', () => {
    const { rerender } = render(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    const input = screen.getByPlaceholderText('Enter scenario name');
    fireEvent.change(input, { target: { value: 'Modified Name' } });
    expect(input).toHaveValue('Modified Name');

    // Close dialog
    rerender(
      <ScenarioNameDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        currentName=""
        onConfirm={mockOnConfirm}
      />
    );

    // Reopen with new current name
    rerender(
      <ScenarioNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        currentName="New Default"
        onConfirm={mockOnConfirm}
      />
    );

    const reopenedInput = screen.getByPlaceholderText('Enter scenario name');
    expect(reopenedInput).toHaveValue('New Default');
  });
});
