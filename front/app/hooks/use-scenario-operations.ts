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

import useError from '~/hooks/use-error';
import { log, LogLevel } from '~/lib/logger';
import api from '~/api';

/**
 * Custom hook for scenario operations (export, save, load, import)
 */
export function useScenarioOperations() {
  const { displayError } = useError();

  /**
   * Validates scenario content and returns parsed JSON
   * @returns Parsed content if valid, null if invalid
   */
  const validateContent = async (content: string) => {
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
    try {
      const response = await api.post('/scenarios/validate', {
        content: parsedContent,
      });
      const result = response.data;
      if (!result.valid) {
        const errors = Array.isArray(result.errors)
          ? result.errors
          : [result.errors].filter(Boolean);
        displayError(
          'Scenario validation failed',
          errors.map((e: string) => `• ${e}`).join('\n')
        );
        return null;
      }
      if (result.warnings && result.warnings.length > 0) {
        console.warn('Scenario warnings:', result.warnings.join('\n'));
      }
      return parsedContent;
    } catch (error: unknown) {
      let message = 'Unknown error';
      if (error && typeof error === 'object') {
        const errorObj = error as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        message =
          errorObj.response?.data?.detail || errorObj.message || message;
      }
      displayError('Validation error', message);
      return null;
    }
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
      log({
        message: 'Scenario download failed',
        level: LogLevel.ERROR,
        stack: error instanceof Error ? error.stack : undefined,
      });
    }
  };

  // Exports scenario content as a JSON file
  const exportScenario = async (content: string, scenarioName: string) => {
    const parsedContent = await validateContent(content);
    if (!parsedContent) return false;

    const contentToExport = JSON.stringify(parsedContent, null, 2);
    log({
      message: 'Scenario exported',
      level: LogLevel.INFO,
    });
    downloadJSON(contentToExport, scenarioName);
    return true;
  };

  // Saves scenario to backend
  const saveScenario = async (
    content: string,
    scenarioName: string,
    description: string = ''
  ) => {
    const parsedContent = await validateContent(content);
    if (!parsedContent) return false;

    try {
      await api.post('/scenarios', {
        name: scenarioName,
        content: parsedContent,
        description,
        allow_duplicate_name: true,
      });
      alert('Scenario saved successfully!');
    } catch (error: unknown) {
      let message = 'Unknown error';
      if (error && typeof error === 'object') {
        const errorObj = error as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        message =
          errorObj.response?.data?.detail || errorObj.message || message;
      }
      displayError('Failed to save scenario', message);
    }
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
    log({
      message: 'Scenario imported',
      level: LogLevel.INFO,
    });
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
