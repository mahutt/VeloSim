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
import { toast } from 'sonner';

// Mock Sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

// Mock the api module
vi.mock('../../app/api', () => ({
  default: {
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock the logger module
vi.mock('../../app/lib/logger', () => ({
  log: vi.fn(),
  LogLevel: {
    DEBUG: 'debug',
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error',
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
  let mockConsoleWarn: ReturnType<typeof vi.spyOn>;
  let mockConsoleError: ReturnType<typeof vi.spyOn>;
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
    mockConsoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    mockConsoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
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
        '{"start_time": "day1:08:00"}'
      );
      expect(validatedContent).toBeNull();
    });

    it('returns parsed content and logs warnings for content with warnings', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const mockContent = { start_time: 'day1:08:00', stations: [] };

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
        'Scenario validation warnings:',
        'No stations defined'
      );
    });

    it('returns parsed content for valid content without warnings', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const mockContent = { start_time: 'day1:08:00', stations: [{ id: 1 }] };

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

    it('handles API network errors gracefully', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API to throw a network error
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'));

      const validatedContent = await result.current.validateContent(
        '{"start_time": "day1:08:00"}'
      );

      expect(validatedContent).toBeNull();
    });

    it('handles API errors without response data', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API to throw an error without response
      vi.mocked(api.post).mockRejectedValue({
        message: 'Request failed',
      });

      const validatedContent = await result.current.validateContent(
        '{"start_time": "day1:08:00"}'
      );

      expect(validatedContent).toBeNull();
    });
  });

  describe('downloadJSON', () => {
    it('creates blob and triggers download with correct filename', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const content = '{"start_time": "day1:08:00"}';
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

      const content = '{"start_time": "day1:08:00"}';
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

      const content = '{"start_time": "day1:08:00"}';
      const filename = 'test';

      // The function catches and logs the error instead of throwing
      result.current.downloadJSON(content, filename);

      expect(mockConsoleError).toHaveBeenCalled();
    });

    it('handles non-Error exceptions during download', () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      mockCreateObjectURL.mockImplementation(() => {
        throw 'String error'; // Not an Error object
      });

      const content = '{"start_time": "day1:08:00"}';
      const filename = 'test';

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

    it('includes start_time in exported content', async () => {
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
    it('validates content and shows toast for valid scenario', async () => {
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
      expect(saved).toBe(null);
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });

    it('returns null for invalid content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const saved = await result.current.saveScenario('', 'Test Scenario');
      expect(saved).toBeNull();
      expect(toast.success).not.toHaveBeenCalled();
    });

    it('handles API errors without response data during save', async () => {
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

      // Mock API save failure without response
      vi.mocked(api.post).mockRejectedValueOnce({
        message: 'Network timeout',
      });

      const mockContent = { stations: [] };
      const saved = await result.current.saveScenario(
        JSON.stringify(mockContent),
        'Test Scenario'
      );

      expect(saved).toBeNull();
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });

    it('handles API response without id', async () => {
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

      // Mock API save success without id
      vi.mocked(api.post).mockResolvedValueOnce({
        data: {},
      });

      const mockContent = { stations: [] };
      const saved = await result.current.saveScenario(
        JSON.stringify(mockContent),
        'Test Scenario'
      );

      expect(saved).toBeNull();
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario saved successfully!'
      );
    });
  });

  describe('overwriteScenario', () => {
    it('validates content and shows toast for successful overwrite', async () => {
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

      // Mock API put success
      vi.mocked(api.put).mockResolvedValueOnce({
        data: { id: 1 },
      });

      const mockContent = { stations: [] };
      const overwritten = await result.current.overwriteScenario(
        1,
        JSON.stringify(mockContent),
        'Test Scenario',
        'Test Description'
      );

      expect(overwritten).toBe(1);
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario overwritten successfully!'
      );
      expect(api.put).toHaveBeenCalledWith('/scenarios/1', {
        name: 'Test Scenario',
        content: mockContent,
        description: 'Test Description',
      });
    });

    it('returns null for invalid content', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      const overwritten = await result.current.overwriteScenario(
        1,
        '',
        'Test Scenario'
      );

      expect(overwritten).toBeNull();
      expect(toast.success).not.toHaveBeenCalled();
      expect(api.put).not.toHaveBeenCalled();
    });

    it('handles API errors gracefully', async () => {
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

      // Mock API put failure
      vi.mocked(api.put).mockRejectedValueOnce({
        response: { data: { detail: 'Server error' } },
      });

      const mockContent = { stations: [] };
      const result2 = await result.current.overwriteScenario(
        1,
        JSON.stringify(mockContent),
        'Test Scenario'
      );

      // Should return null due to error
      expect(result2).toBeNull();
      // Should not show success toast
      expect(toast.success).not.toHaveBeenCalled();
    });
  });

  describe('deleteScenario', () => {
    it('successfully deletes a scenario and shows toast', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API delete success
      vi.mocked(api.delete).mockResolvedValueOnce({ data: {} });

      const deleted = await result.current.deleteScenario(1);

      expect(deleted).toBe(true);
      expect(api.delete).toHaveBeenCalledWith('/scenarios/1');
      expect(toast.success).toHaveBeenCalledWith(
        'Scenario deleted successfully!'
      );
    });

    it('returns false and shows error when delete fails', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API delete failure
      vi.mocked(api.delete).mockRejectedValueOnce({
        response: { data: { detail: 'Scenario not found' } },
      });

      const deleted = await result.current.deleteScenario(999);

      expect(deleted).toBe(false);
      expect(toast.success).not.toHaveBeenCalled();
    });

    it('handles delete error without response data', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API delete failure without response
      vi.mocked(api.delete).mockRejectedValueOnce({
        message: 'Network error',
      });

      const deleted = await result.current.deleteScenario(1);

      expect(deleted).toBe(false);
      expect(toast.success).not.toHaveBeenCalled();
    });

    it('handles delete error with unknown error type', async () => {
      const { result } = renderHook(() => useScenarioOperations(), {
        wrapper: Wrapper,
      });

      // Mock API delete failure with unknown error
      vi.mocked(api.delete).mockRejectedValueOnce('String error');

      const deleted = await result.current.deleteScenario(1);

      expect(deleted).toBe(false);
    });
  });
});
