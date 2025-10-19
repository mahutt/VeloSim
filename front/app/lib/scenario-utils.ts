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

import type { Scenario } from '~/types';

/**
 * Helper function to get a preview text for a scenario
 * Used for displaying in the sidebar
 */
export const getScenarioPreview = (scenario: Scenario): string => {
  try {
    const parsed = JSON.parse(scenario.content);
    const keys = Object.keys(parsed);
    if (keys.length === 0) return 'Empty scenario';
    return `${keys.length} ${keys.length === 1 ? 'property' : 'properties'}`;
  } catch {
    return 'Invalid data';
  }
};

/**
 * Load saved scenarios from placeholder data
 * TODO: Replace with actual API call to backend
 */
export const loadSavedScenarios = async (): Promise<Scenario[]> => {
  try {
    const response = await fetch('/placeholder-data/saved-scenarios.json');
    const data = await response.json();
    return data;
  } catch {
    return [];
  }
};
