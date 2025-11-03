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

import {
  validateScenario,
  formatValidationResults,
} from '~/lib/scenario-validation';
import useError from '~/hooks/use-error';

/**
 * Custom hook for scenario operations (export, save, load, import)
 */
export function useScenarioOperations() {
  const { displayError } = useError();

  /**
   * Validates scenario content and returns parsed JSON
   * @returns Parsed content if valid, null if invalid
   */
  const validateContent = (content: string) => {
    // Validate that there's content
    if (!content.trim()) {
      displayError(
        'No content to process',
        'Please enter or load a scenario first.'
      );
      return null;
    }

    // Validate JSON format
    let parsedContent;
    try {
      parsedContent = JSON.parse(content);
    } catch {
      displayError(
        'Invalid JSON format',
        'The scenario content is not valid JSON. Please fix the formatting.'
      );
      return null;
    }

    // Validate scenario structure
    const validationResult = validateScenario(parsedContent);
    if (!validationResult.valid) {
      displayError(
        'Scenario validation failed',
        formatValidationResults(validationResult)
      );
      return null;
    }

    // Show warnings if any (but continue)
    if (validationResult.warnings.length > 0) {
      console.warn(
        'Scenario warnings:',
        formatValidationResults(validationResult)
      );
    }

    return parsedContent;
  };

  // Downloads JSON content as a file
  const downloadJSON = (content: string, filename: string) => {
    try {
      // Sanitize filename (replace spaces with underscores)
      const sanitizedFilename = filename.replace(/\s+/g, '_');
      const fullFilename = `${sanitizedFilename}.json`;

      // Create blob and download
      const blob = new Blob([content], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fullFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download error:', error);
      displayError(
        'Download failed',
        'An unexpected error occurred while downloading the file. Please try again.'
      );
    }
  };

  // Exports scenario content as a JSON file
  const exportScenario = (content: string, scenarioName: string) => {
    const parsedContent = validateContent(content);
    if (!parsedContent) return false;

    const contentToExport = JSON.stringify(parsedContent, null, 2);
    downloadJSON(contentToExport, scenarioName);
    return true;
  };

  // Saves scenario to backend
  const saveScenario = (content: string, scenarioName: string) => {
    const parsedContent = validateContent(content);
    if (!parsedContent) return false;

    // TODO: Add API call to backend
    console.log('Save scenario:', scenarioName);
    alert('Save Scenario - TODO: Implement backend integration');
    return true;
  };

  // Loads scenario from backend
  const loadScenario = (scenarioId: number) => {
    // TODO: Add API call to backend
    console.log('Load scenario:', scenarioId);
    alert('Load Scenario - TODO: Implement backend integration');
  };

  // Imports scenario from file
  const importScenario = () => {
    // TODO: Add file picker and import logic
    console.log('Import scenario clicked');
    alert('Import Scenario - TODO: Implement import functionality');
  };

  return {
    validateContent,
    downloadJSON,
    exportScenario,
    saveScenario,
    loadScenario,
    importScenario,
  };
}
