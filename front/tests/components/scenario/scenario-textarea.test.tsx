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
import { render, fireEvent, screen } from '@testing-library/react';
import ScenarioTextArea from '../../../app/components/scenario/scenario-textarea';

describe('ScenarioTextArea', () => {
  const setup = (propsOverride = {}) => {
    const props = {
      scenarioData: '{"foo":"bar"}',
      error: null,
      onChange: vi.fn(),
      onSave: vi.fn(),
      onExport: vi.fn(),
      onStart: vi.fn(),
      ...propsOverride,
    };
    render(<ScenarioTextArea {...props} />);
    return props;
  };

  it('renders textarea with scenario data', () => {
    setup();
    const textarea = screen.getByLabelText(
      'Scenario JSON data'
    ) as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    expect(textarea.value).toBe('{"foo":"bar"}');
  });

  it('calls onChange when textarea value changes', () => {
    const { onChange } = setup();
    const textarea = screen.getByLabelText('Scenario JSON data');
    fireEvent.change(textarea, { target: { value: '{"baz":"qux"}' } });
    expect(onChange).toHaveBeenCalledWith('{"baz":"qux"}');
  });

  it('renders error message when error is provided', () => {
    setup({ error: 'Invalid JSON' });
    expect(screen.getByText('Invalid JSON')).toBeInTheDocument();
  });

  it('calls onSave when Save button is clicked', () => {
    const { onSave } = setup();
    const saveButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(saveButton);
    expect(onSave).toHaveBeenCalled();
  });

  it('calls onExport when Export button is clicked', () => {
    const { onExport } = setup();
    const exportButton = screen.getByRole('button', { name: /export/i });
    fireEvent.click(exportButton);
    expect(onExport).toHaveBeenCalled();
  });

  it('calls onStart when Start Simulation button is clicked', () => {
    const { onStart } = setup();
    const startButton = screen.getByRole('button', {
      name: /start simulation/i,
    });
    fireEvent.click(startButton);
    expect(onStart).toHaveBeenCalled();
  });
});
