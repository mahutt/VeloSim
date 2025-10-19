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
import { getScenarioPreview, loadSavedScenarios } from '~/lib/scenario-utils';
import type { Scenario } from '~/types';

describe('getScenarioPreview', () => {
  it('returns property count for valid JSON with multiple properties', () => {
    const scenario: Scenario = {
      id: 1,
      name: 'Test',
      user_id: 1,
      content: '{"stations": [], "resources": [], "config": {}}',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    };

    const result = getScenarioPreview(scenario);
    expect(result).toBe('3 properties');
  });

  it('returns singular "property" for JSON with one property', () => {
    const scenario: Scenario = {
      id: 1,
      name: 'Test',
      user_id: 1,
      content: '{"stations": []}',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    };

    const result = getScenarioPreview(scenario);
    expect(result).toBe('1 property');
  });

  it('returns "Empty scenario" for JSON with no properties', () => {
    const scenario: Scenario = {
      id: 1,
      name: 'Test',
      user_id: 1,
      content: '{}',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    };

    const result = getScenarioPreview(scenario);
    expect(result).toBe('Empty scenario');
  });

  it('returns "Invalid data" for malformed JSON', () => {
    const scenario: Scenario = {
      id: 1,
      name: 'Test',
      user_id: 1,
      content: 'not valid json',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    };

    const result = getScenarioPreview(scenario);
    expect(result).toBe('Invalid data');
  });

  it('returns "Invalid data" for empty string content', () => {
    const scenario: Scenario = {
      id: 1,
      name: 'Test',
      user_id: 1,
      content: '',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    };

    const result = getScenarioPreview(scenario);
    expect(result).toBe('Invalid data');
  });
});

describe('loadSavedScenarios', () => {
  const mockScenarios: Scenario[] = [
    {
      id: 1,
      name: 'Mock Scenario 1',
      user_id: 1,
      content: '{"stations": []}',
      date_created: '2025-01-15T08:30:00Z',
      date_updated: '2025-01-15T08:30:00Z',
    },
    {
      id: 2,
      name: 'Mock Scenario 2',
      user_id: 1,
      content: '{"resources": []}',
      date_created: '2025-01-16T10:15:00Z',
      date_updated: '2025-01-16T14:22:00Z',
    },
  ];

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns scenarios when fetch is successful', async () => {
    const mockResponse = {
      ok: true,
      json: async () => mockScenarios,
    } as Response;

    vi.mocked(global.fetch).mockResolvedValueOnce(mockResponse);

    const result = await loadSavedScenarios();

    expect(global.fetch).toHaveBeenCalledWith(
      '/placeholder-data/saved-scenarios.json'
    );
    expect(result).toEqual(mockScenarios);
  });

  it('returns empty array when fetch fails', async () => {
    vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Network error'));

    const result = await loadSavedScenarios();

    expect(result).toEqual([]);
  });

  it('returns empty array when response is not ok', async () => {
    const mockResponse = {
      ok: false,
      json: async () => {
        throw new Error('Parse error');
      },
    } as unknown as Response;

    vi.mocked(global.fetch).mockResolvedValueOnce(mockResponse);

    const result = await loadSavedScenarios();

    expect(result).toEqual([]);
  });

  it('returns empty array when JSON parsing fails', async () => {
    const mockResponse = {
      ok: true,
      json: async () => {
        throw new Error('Invalid JSON');
      },
    } as unknown as Response;

    vi.mocked(global.fetch).mockResolvedValueOnce(mockResponse);

    const result = await loadSavedScenarios();

    expect(result).toEqual([]);
  });
});
