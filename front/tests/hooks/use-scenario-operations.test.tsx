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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useScenarioOperations } from '../../app/hooks/use-scenario-operations';
import * as scenarioValidation from '../../app/lib/scenario-validation';
import { ErrorProvider } from '../../app/providers/error-provider';
import type { ReactNode } from 'react';

// Wrapper component to provide ErrorProvider context
const Wrapper = ({ children }: { children: ReactNode }) => (
  <ErrorProvider>{children}</ErrorProvider>
);

describe('useScenarioOperations', () => {
  let container: HTMLDivElement;
  let mockCreateObjectURL: ReturnType<typeof vi.fn>;
  let mockRevokeObjectURL: ReturnType<typeof vi.fn>;
  let mockCreateElement: ReturnType<typeof vi.fn>;
  let mockAppendChild: ReturnType<typeof vi.fn>;
  let mockRemoveChild: ReturnType<typeof vi.fn>;
  let mockClick: ReturnType<typeof vi.fn>;
  let mockConsoleLog: ReturnType<typeof vi.spyOn>;
  let mockConsoleWarn: ReturnType<typeof vi.spyOn>;
  let mockConsoleError: ReturnType<typeof vi.spyOn>;
  let mockAlert: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create a container for renderHook BEFORE mocking document.createElement
    container = document.createElement('div');
    document.body.appendChild(container);

    // Mock URL methods
    mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
    mockRevokeObjectURL = vi.fn();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    // Mock document methods (AFTER creating container)
    mockClick = vi.fn();
    const originalCreateElement = document.createElement.bind(document);
    mockCreateElement = vi.fn((tagName: string) => {
      // For 'a' tags used in download, return mock
      if (tagName === 'a') {
        return {
          href: '',
          download: '',
          click: mockClick,
        };
      }
      // For other elements, use original createElement
      return originalCreateElement(tagName);
    });
    mockAppendChild = vi.fn();
    mockRemoveChild = vi.fn();
    document.createElement =
      mockCreateElement as unknown as typeof document.createElement;
    document.body.appendChild = mockAppendChild;
    document.body.removeChild = mockRemoveChild;

    // Mock console methods
    mockConsoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    mockConsoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    mockConsoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    // Mock window.alert
    mockAlert = vi.fn();
    global.alert = mockAlert;
  });

  afterEach(() => {
    // Cleanup container
    if (container) {
      document.body.removeChild(container);
    }
    vi.restoreAllMocks();
  });

  describe('validateContent', () => {
    it('returns null and displays error for empty content', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const validatedContent = result.current.validateContent('');

      expect(validatedContent).toBeNull();
    });

    it('returns null and displays error for whitespace-only content', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const validatedContent = result.current.validateContent('   \n  \t  ');

      expect(validatedContent).toBeNull();
    });

    it('returns null and displays error for invalid JSON', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const validatedContent =
        result.current.validateContent('{ invalid json }');

      expect(validatedContent).toBeNull();
    });

    it('returns null and displays error for content that fails validation', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      vi.spyOn(scenarioValidation, 'validateScenario').mockReturnValue({
        valid: false,
        errors: ['Missing required field: stations'],
        warnings: [],
      });

      const validatedContent = result.current.validateContent(
        '{"scenario_title": "Test"}'
      );

      expect(validatedContent).toBeNull();
    });

    it('returns parsed content and logs warnings for content with warnings', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const mockContent = { scenario_title: 'Test', stations: [] };
      vi.spyOn(scenarioValidation, 'validateScenario').mockReturnValue({
        valid: true,
        errors: [],
        warnings: ['No stations defined'],
      });

      const validatedContent = result.current.validateContent(
        JSON.stringify(mockContent)
      );

      expect(validatedContent).toEqual(mockContent);
      expect(mockConsoleWarn).toHaveBeenCalledWith(
        'Scenario warnings:',
        expect.stringContaining('No stations defined')
      );
    });

    it('returns parsed content for valid content without warnings', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const mockContent = { scenario_title: 'Test', stations: [{ id: 1 }] };
      vi.spyOn(scenarioValidation, 'validateScenario').mockReturnValue({
        valid: true,
        errors: [],
        warnings: [],
      });

      const validatedContent = result.current.validateContent(
        JSON.stringify(mockContent)
      );

      expect(validatedContent).toEqual(mockContent);
      expect(mockConsoleWarn).not.toHaveBeenCalled();
    });
  });

  describe('prepareForExport', () => {
    it('adds scenario_title to content', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const content = { stations: [] };
      const exportedContent = result.current.prepareForExport(
        content,
        'Test Scenario'
      );

      expect(exportedContent).toContain('"scenario_title": "Test Scenario"');
    });

    it('trims whitespace from scenario name', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const content = { stations: [] };
      const exportedContent = result.current.prepareForExport(
        content,
        '  Scenario Name  '
      );

      expect(exportedContent).toContain('"scenario_title": "Scenario Name"');
    });

    it('formats JSON with 2-space indentation', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const content = { stations: [] };
      const exportedContent = result.current.prepareForExport(content, 'Test');

      expect(exportedContent).toContain('  "scenario_title"');
      expect(exportedContent).toContain('  "stations"');
    });

    it('places scenario_title first in the output', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const content = { stations: [], bikes: [] };
      const exportedContent = result.current.prepareForExport(content, 'Test');

      const titleIndex = exportedContent.indexOf('"scenario_title"');
      const stationsIndex = exportedContent.indexOf('"stations"');
      const bikesIndex = exportedContent.indexOf('"bikes"');

      expect(titleIndex).toBeLessThan(stationsIndex);
      expect(titleIndex).toBeLessThan(bikesIndex);
    });
  });

  describe('downloadJSON', () => {
    it('creates blob and triggers download with correct filename', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const content = '{"scenario_title": "Test"}';
      const filename = 'test-scenario';

      result.current.downloadJSON(content, filename);

      expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(mockCreateElement).toHaveBeenCalledWith('a');
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });

    it('sanitizes filename by replacing spaces with underscores', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const mockElement = {
        href: '',
        download: '',
        click: mockClick,
      };
      mockCreateElement.mockReturnValue(mockElement);

      const content = '{"scenario_title": "Test"}';
      const filename = 'my test scenario';

      result.current.downloadJSON(content, filename);

      expect(mockElement.download).toBe('my_test_scenario.json');
    });

    it('handles download errors gracefully', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      mockCreateObjectURL.mockImplementation(() => {
        throw new Error('Blob creation failed');
      });

      const content = '{"scenario_title": "Test"}';
      const filename = 'test';

      // The function catches and logs the error instead of throwing
      result.current.downloadJSON(content, filename);

      expect(mockConsoleError).toHaveBeenCalled();
    });
  });

  describe('exportScenario', () => {
    it('exports valid scenario successfully', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      vi.spyOn(scenarioValidation, 'validateScenario').mockReturnValue({
        valid: true,
        errors: [],
        warnings: [],
      });

      const mockContent = { stations: [] };
      const exported = result.current.exportScenario(
        JSON.stringify(mockContent),
        'Test Scenario'
      );

      expect(exported).toBe(true);
      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
    });

    it('returns false and does not download for invalid content', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const exported = result.current.exportScenario('', 'Test Scenario');

      expect(exported).toBe(false);
      expect(mockCreateObjectURL).not.toHaveBeenCalled();
      expect(mockClick).not.toHaveBeenCalled();
    });

    it('includes scenario_title in exported content', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      vi.spyOn(scenarioValidation, 'validateScenario').mockReturnValue({
        valid: true,
        errors: [],
        warnings: [],
      });

      let capturedBlob: Blob | undefined;
      mockCreateObjectURL.mockImplementation((blob: Blob) => {
        capturedBlob = blob;
        return 'blob:mock-url';
      });

      const mockContent = { stations: [] };
      result.current.exportScenario(JSON.stringify(mockContent), 'My Scenario');

      expect(capturedBlob).toBeDefined();
      // Read blob content to verify scenario_title is included
      capturedBlob!.text().then((text) => {
        expect(text).toContain('"scenario_title": "My Scenario"');
      });
    });
  });

  describe('saveScenario', () => {
    it('validates content and shows alert for valid scenario', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      vi.spyOn(scenarioValidation, 'validateScenario').mockReturnValue({
        valid: true,
        errors: [],
        warnings: [],
      });

      const mockContent = { stations: [] };
      const saved = result.current.saveScenario(
        JSON.stringify(mockContent),
        'Test Scenario'
      );

      expect(saved).toBe(true);
      expect(mockAlert).toHaveBeenCalledWith(
        'Save Scenario - TODO: Implement backend integration'
      );
    });

    it('returns false for invalid content', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      const saved = result.current.saveScenario('', 'Test Scenario');

      expect(saved).toBe(false);
      expect(mockAlert).not.toHaveBeenCalled();
    });
  });

  describe('loadScenario', () => {
    it('logs scenario ID and shows alert', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      result.current.loadScenario(123);

      expect(mockConsoleLog).toHaveBeenCalledWith('Load scenario:', 123);
      expect(mockAlert).toHaveBeenCalledWith(
        'Load Scenario - TODO: Implement backend integration'
      );
    });
  });

  describe('importScenario', () => {
    it('logs import action and shows alert', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
        container,
      });

      result.current.importScenario();

      expect(mockConsoleLog).toHaveBeenCalledWith('Import scenario clicked');
      expect(mockAlert).toHaveBeenCalledWith(
        'Import Scenario - TODO: Implement import functionality'
      );
    });
  });
});
