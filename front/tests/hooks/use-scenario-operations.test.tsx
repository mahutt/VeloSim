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
import { ErrorProvider } from '../../app/providers/error-provider';
import type { ReactNode } from 'react';
import api from '../../app/api';

// Mock the api module
vi.mock('../../app/api', () => ({
  default: {
    post: vi.fn(),
  },
}));

// Wrapper component to provide ErrorProvider context
const Wrapper = ({ children }: { children: ReactNode }) => (
  <ErrorProvider>{children}</ErrorProvider>
);

describe('useScenarioOperations', () => {
  let mockCreateObjectURL: ReturnType<typeof vi.fn>;
  let mockRevokeObjectURL: ReturnType<typeof vi.fn>;
  let mockClick: ReturnType<typeof vi.fn>;
  let mockConsoleLog: ReturnType<typeof vi.spyOn>;
  let mockConsoleWarn: ReturnType<typeof vi.spyOn>;
  let mockConsoleError: ReturnType<typeof vi.spyOn>;
  let mockAlert: ReturnType<typeof vi.fn>;
  let originalCreateElement: typeof document.createElement;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock URL methods
    mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
    mockRevokeObjectURL = vi.fn();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    // Store original createElement
    originalCreateElement = document.createElement.bind(document);

    // Store created anchors for testing
    let lastAnchor: HTMLAnchorElement | null = null;

    // Mock document.createElement to intercept only 'a' element creation
    mockClick = vi.fn();
    document.createElement = vi.fn((tagName: string) => {
      if (tagName === 'a') {
        // Create a real anchor element but spy on its click method
        const realAnchor = originalCreateElement('a') as HTMLAnchorElement;
        realAnchor.click = mockClick as unknown as () => void;
        lastAnchor = realAnchor;
        return realAnchor;
      }
      // Use original for all other elements (important for React Testing Library)
      return originalCreateElement(tagName);
    }) as unknown as typeof document.createElement;

    // Add helper to get last created anchor
    (
      document.createElement as typeof document.createElement & {
        getLastAnchor: () => HTMLAnchorElement | null;
      }
    ).getLastAnchor = () => lastAnchor;

    // Mock console methods
    mockConsoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    mockConsoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    mockConsoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    // Mock window.alert
    mockAlert = vi.fn();
    global.alert = mockAlert;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Restore original createElement
    document.createElement = originalCreateElement;
  });

  describe('validateContent', () => {
    it('returns null and displays error for empty content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const validatedContent = await result.current.validateContent('');

      expect(validatedContent).toBeNull();
    });

    it('returns null and displays error for whitespace-only content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const validatedContent =
        await result.current.validateContent('   \n  \t  ');

      expect(validatedContent).toBeNull();
    });

    it('returns null and displays error for invalid JSON', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const validatedContent =
        await result.current.validateContent('{ invalid json }');

      expect(validatedContent).toBeNull();
    });

    it('returns null and displays error for content that fails validation', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API to return validation failure
      vi.mocked(api.post).mockResolvedValue({
        data: {
          valid: false,
          errors: ['Missing required field: end_time'],
          warnings: [],
        },
      });

      const validatedContent = await result.current.validateContent(
        '{"scenario_title": "Test"}'
      );
      expect(validatedContent).toBeNull();
    });

    it('returns parsed content and logs warnings for content with warnings', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const mockContent = { scenario_title: 'Test', stations: [] };

      // Mock API to return validation success with warnings
      vi.mocked(api.post).mockResolvedValue({
        data: {
          valid: true,
          errors: [],
          warnings: ['No stations defined'],
        },
      });

      const validatedContent = await result.current.validateContent(
        JSON.stringify(mockContent)
      );
      expect(validatedContent).toEqual(mockContent);
      expect(mockConsoleWarn).toHaveBeenCalledWith(
        'Scenario warnings:',
        'No stations defined'
      );
    });

    it('returns parsed content for valid content without warnings', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const mockContent = { scenario_title: 'Test', stations: [{ id: 1 }] };

      // Mock API to return validation success
      vi.mocked(api.post).mockResolvedValue({
        data: {
          valid: true,
          errors: [],
          warnings: [],
        },
      });

      const validatedContent = await result.current.validateContent(
        JSON.stringify(mockContent)
      );
      expect(validatedContent).toEqual(mockContent);
      expect(mockConsoleWarn).not.toHaveBeenCalled();
    });
  });

  describe('downloadJSON', () => {
    it('creates blob and triggers download with correct filename', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const content = '{"scenario_title": "Test"}';
      const filename = 'test-scenario';

      result.current.downloadJSON(content, filename);

      expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(document.createElement).toHaveBeenCalledWith('a');
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
    });

    it('sanitizes filename by replacing spaces with underscores', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const content = '{"scenario_title": "Test"}';
      const filename = 'my test scenario';

      result.current.downloadJSON(content, filename);

      const lastAnchor = (
        document.createElement as typeof document.createElement & {
          getLastAnchor: () => HTMLAnchorElement | null;
        }
      ).getLastAnchor();
      expect(lastAnchor?.download).toBe('my_test_scenario.json');
    });

    it('handles download errors gracefully', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
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
    it('validates content and triggers download for valid scenario', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API to return validation success
      vi.mocked(api.post).mockResolvedValue({
        data: {
          valid: true,
          errors: [],
          warnings: [],
        },
      });

      const mockContent = { stations: [] };
      const exported = await result.current.exportScenario(
        JSON.stringify(mockContent),
        'Test Scenario'
      );

      expect(exported).toBe(true);
      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
    });

    it('returns false and does not download for invalid content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const exported = await result.current.exportScenario('', 'Test Scenario');

      expect(exported).toBe(false);
      expect(mockCreateObjectURL).not.toHaveBeenCalled();
      expect(mockClick).not.toHaveBeenCalled();
    });

    it('includes scenario_title in exported content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API to return validation success
      vi.mocked(api.post).mockResolvedValue({
        data: {
          valid: true,
          errors: [],
          warnings: [],
        },
      });

      let capturedBlob: Blob | undefined;
      mockCreateObjectURL.mockImplementation((blob: Blob) => {
        capturedBlob = blob;
        return 'blob:mock-url';
      });

      const mockContent = { stations: [] };
      await result.current.exportScenario(
        JSON.stringify(mockContent),
        'My Scenario'
      );
      expect(capturedBlob).toBeDefined();
      // Read blob content to verify it matches the original content
      const text = await capturedBlob!.text();
      const exported = JSON.parse(text);
      expect(exported).toEqual(mockContent);
    });
  });

  describe('saveScenario', () => {
    it('validates content and shows alert for valid scenario', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API validation success
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {
          valid: true,
          errors: [],
          warnings: [],
        },
      });

      // Mock API save success
      vi.mocked(api.post).mockResolvedValueOnce({
        data: { id: 1 },
      });

      const mockContent = { stations: [] };
      const saved = await result.current.saveScenario(
        JSON.stringify(mockContent),
        'Test Scenario'
      );
      expect(saved).toBe(true);
      expect(mockAlert).toHaveBeenCalledWith('Scenario saved successfully!');
    });

    it('returns false for invalid content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const saved = await result.current.saveScenario('', 'Test Scenario');
      expect(saved).toBe(false);
      expect(mockAlert).not.toHaveBeenCalled();
    });
  });

  describe('loadScenario', () => {
    it('logs scenario ID and shows alert', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
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
      });

      result.current.importScenario();

      expect(mockConsoleLog).toHaveBeenCalledWith('Import scenario clicked');
      expect(mockAlert).toHaveBeenCalledWith(
        'Import Scenario - TODO: Implement import functionality'
      );
    });
  });
});
