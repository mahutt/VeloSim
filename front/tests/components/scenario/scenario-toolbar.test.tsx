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

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import ScenarioToolbar from '../../../app/components/scenario/scenario-toolbar';

describe('ScenarioToolbar', () => {
  const setup = (propsOverride = {}) => {
    const props = {
      scenarioName: 'Test Scenario',
      onNameChange: vi.fn(),
      onImport: vi.fn(),
      onNew: vi.fn(),
      isEditMode: false,
      isExistingScenario: false,
      ...propsOverride,
    };
    const utils = render(<ScenarioToolbar {...props} />);
    return { ...utils, props };
  };

  it('renders input with scenario name', () => {
    const { getByLabelText } = setup();
    const input = getByLabelText('Scenario name') as HTMLInputElement;
    expect(input.value).toBe('Test Scenario');
  });

  it('calls onNameChange when input changes', () => {
    const { getByLabelText, props } = setup();
    const input = getByLabelText('Scenario name') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'New Name' } });
    expect(props.onNameChange).toHaveBeenCalledWith('New Name');
  });

  it('calls onImport when Import button is clicked', () => {
    const { getByText, props } = setup();
    const importBtn = getByText('Import');
    fireEvent.click(importBtn);
    expect(props.onImport).toHaveBeenCalled();
  });

  it('calls onNew when New button is clicked', () => {
    const { getByText, props } = setup();
    const newBtn = getByText('New');
    fireEvent.click(newBtn);
    expect(props.onNew).toHaveBeenCalled();
  });

  it('renders both Import and New buttons', () => {
    const { getByText } = setup();
    expect(getByText('Import')).toBeInTheDocument();
    expect(getByText('New')).toBeInTheDocument();
  });
});
