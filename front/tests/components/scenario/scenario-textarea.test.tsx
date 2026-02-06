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
      scenarioDescription: '',
      onChange: vi.fn(),
      onDescriptionChange: vi.fn(),
      onSave: vi.fn(),
      onExport: vi.fn(),
      onStart: vi.fn(),
      isEditMode: false,
      hasExistingFilename: false,
      isExistingScenario: false,
      onEdit: vi.fn(),
      ...propsOverride,
    };
    render(<ScenarioTextArea {...props} />);
    return props;
  };

  it('renders textarea with scenario data', () => {
    setup();
    const textarea = screen.getByLabelText(
      'Scenario JSON'
    ) as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    expect(textarea.value).toBe('{"foo":"bar"}');
  });

  it('calls onChange when textarea value changes', () => {
    const { onChange } = setup();
    const textarea = screen.getByLabelText('Scenario JSON');
    fireEvent.change(textarea, { target: { value: '{"baz":"qux"}' } });
    expect(onChange).toHaveBeenCalledWith('{"baz":"qux"}');
  });

  // Inline error rendering test removed: errors are now shown in a global dialog/modal.

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

  describe('Tab key handling (lines 46-63)', () => {
    it('inserts 2 spaces when Tab is pressed', () => {
      const { onChange } = setup({ scenarioData: 'test' });
      const textarea = screen.getByLabelText(
        'Scenario JSON'
      ) as HTMLTextAreaElement;

      // Set cursor position at the end
      textarea.selectionStart = 4;
      textarea.selectionEnd = 4;

      fireEvent.keyDown(textarea, { key: 'Tab' });

      expect(onChange).toHaveBeenCalledWith('test  ');
    });

    it('inserts 2 spaces at cursor position in middle of text', () => {
      const { onChange } = setup({ scenarioData: 'before after' });
      const textarea = screen.getByLabelText(
        'Scenario JSON'
      ) as HTMLTextAreaElement;

      // Set cursor position between "before" and " after"
      textarea.selectionStart = 6;
      textarea.selectionEnd = 6;

      fireEvent.keyDown(textarea, { key: 'Tab' });

      expect(onChange).toHaveBeenCalledWith('before   after');
    });

    it('replaces selected text with 2 spaces when Tab is pressed', () => {
      const { onChange } = setup({ scenarioData: 'select this text' });
      const textarea = screen.getByLabelText(
        'Scenario JSON'
      ) as HTMLTextAreaElement;

      // Select "this"
      textarea.selectionStart = 7;
      textarea.selectionEnd = 11;

      fireEvent.keyDown(textarea, { key: 'Tab' });

      expect(onChange).toHaveBeenCalledWith('select    text');
    });

    it('inserts 2 spaces at beginning of empty textarea', () => {
      const { onChange } = setup({ scenarioData: '' });
      const textarea = screen.getByLabelText(
        'Scenario JSON'
      ) as HTMLTextAreaElement;

      textarea.selectionStart = 0;
      textarea.selectionEnd = 0;

      fireEvent.keyDown(textarea, { key: 'Tab' });

      expect(onChange).toHaveBeenCalledWith('  ');
    });

    it('does not affect other key presses', () => {
      const { onChange } = setup({ scenarioData: 'test' });
      const textarea = screen.getByLabelText('Scenario JSON');

      fireEvent.keyDown(textarea, { key: 'Enter' });
      fireEvent.keyDown(textarea, { key: 'a' });
      fireEvent.keyDown(textarea, { key: 'Backspace' });

      // onChange should not be called by these keyDown events
      // (it's only called by the change event)
      expect(onChange).not.toHaveBeenCalled();
    });

    it('handles Tab key with multiline JSON content', () => {
      const { onChange } = setup({
        scenarioData: '{\n  "key": "value"\n}',
      });
      const textarea = screen.getByLabelText(
        'Scenario JSON'
      ) as HTMLTextAreaElement;

      // Set cursor at the end of first line
      textarea.selectionStart = 1;
      textarea.selectionEnd = 1;

      fireEvent.keyDown(textarea, { key: 'Tab' });

      expect(onChange).toHaveBeenCalledWith('{  \n  "key": "value"\n}');
    });
  });

  describe('Line numbers', () => {
    it('displays line numbers for each line of content', () => {
      setup({ scenarioData: 'line1\nline2\nline3' });

      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('synchronizes line numbers scroll with textarea scroll', () => {
      const { container } = render(
        <ScenarioTextArea
          scenarioData="line1\nline2\nline3\nline4\nline5"
          scenarioDescription=""
          onChange={vi.fn()}
          onDescriptionChange={vi.fn()}
          onSave={vi.fn()}
          onExport={vi.fn()}
          onStart={vi.fn()}
          isEditMode={false}
          isExistingScenario={false}
          onEdit={vi.fn()}
        />
      );

      const textarea = screen.getByLabelText('Scenario JSON');
      const lineNumbersDiv = container.querySelector(
        '.select-none.overflow-hidden'
      );

      expect(lineNumbersDiv).toBeInTheDocument();

      // Simulate scroll
      Object.defineProperty(textarea, 'scrollTop', {
        writable: true,
        value: 100,
      });

      fireEvent.scroll(textarea);

      // Line numbers should scroll to match
      expect(lineNumbersDiv?.scrollTop).toBe(100);
    });
  });
});
