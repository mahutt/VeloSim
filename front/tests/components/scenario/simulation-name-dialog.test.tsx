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
import SimulationNameDialog from '~/components/scenario/simulation-name-dialog';

describe('SimulationNameDialog', () => {
  const mockOnOpenChange = vi.fn();
  const mockOnStartSimulation = vi.fn();

  beforeEach(() => {
    mockOnOpenChange.mockClear();
    mockOnStartSimulation.mockClear();
  });

  it('renders when open', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    expect(screen.getByText('Name your simulation')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <SimulationNameDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    expect(screen.queryByText('Name your simulation')).not.toBeInTheDocument();
  });

  it('displays scenario name in input by default', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="My Scenario"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const input = screen.getByPlaceholderText('Enter simulation name');
    expect(input).toHaveValue('My Scenario');
  });

  it('allows editing the simulation name', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const input = screen.getByPlaceholderText('Enter simulation name');
    fireEvent.change(input, { target: { value: 'New Simulation Name' } });

    expect(input).toHaveValue('New Simulation Name');
  });

  it('calls onStartSimulation with name when Start button is clicked', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const input = screen.getByPlaceholderText('Enter simulation name');
    fireEvent.change(input, { target: { value: 'Test Simulation' } });

    const startButton = screen.getByRole('button', {
      name: /start/i,
    });
    fireEvent.click(startButton);

    expect(mockOnStartSimulation).toHaveBeenCalledWith('Test Simulation');
  });

  it('disables Start button when name is empty', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const startButton = screen.getByRole('button', {
      name: /start/i,
    });
    expect(startButton).toBeDisabled();
  });

  it('disables Start button when name is only whitespace', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="   "
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const startButton = screen.getByRole('button', {
      name: /start/i,
    });
    expect(startButton).toBeDisabled();
  });

  it('enables Start button when name is provided', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="Valid Name"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const startButton = screen.getByRole('button', {
      name: /start/i,
    });
    expect(startButton).toBeEnabled();
  });

  it('disables Start button when startingSimulation is true', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="Valid Name"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={true}
      />
    );

    const startButton = screen.getByRole('button', {
      name: /start/i,
    });
    expect(startButton).toBeDisabled();
  });

  it('shows loading spinner when startingSimulation is true', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="Valid Name"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={true}
      />
    );

    // Loader2 renders as an SVG with animate-spin class
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('does not show loading spinner when startingSimulation is false', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="Valid Name"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).not.toBeInTheDocument();
  });

  it('closes dialog when Cancel button is clicked', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnStartSimulation).not.toHaveBeenCalled();
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('calls onStartSimulation when Enter key is pressed in input with valid name', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const input = screen.getByPlaceholderText('Enter simulation name');
    fireEvent.change(input, { target: { value: 'Enter Test' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnStartSimulation).toHaveBeenCalledWith('Enter Test');
  });

  it('does not call onStartSimulation with empty name when Enter is pressed', () => {
    render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName=""
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const input = screen.getByPlaceholderText('Enter simulation name');
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnStartSimulation).not.toHaveBeenCalled();
  });

  it('resets name to scenarioName when dialog reopens', () => {
    const { rerender } = render(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="Original Scenario"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const input = screen.getByPlaceholderText('Enter simulation name');
    fireEvent.change(input, { target: { value: 'Modified Name' } });
    expect(input).toHaveValue('Modified Name');

    // Close dialog
    rerender(
      <SimulationNameDialog
        open={false}
        onOpenChange={mockOnOpenChange}
        scenarioName="Original Scenario"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    // Reopen with new scenario name
    rerender(
      <SimulationNameDialog
        open={true}
        onOpenChange={mockOnOpenChange}
        scenarioName="New Scenario"
        onStartSimulation={mockOnStartSimulation}
        startingSimulation={false}
      />
    );

    const reopenedInput = screen.getByPlaceholderText('Enter simulation name');
    expect(reopenedInput).toHaveValue('New Scenario');
  });
});
