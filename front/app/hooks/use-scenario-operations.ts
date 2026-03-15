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
import { log, LogContext, LogLevel } from '~/lib/logger';
import usePreferences from '~/hooks/use-preferences';
import api from '~/api';
import { toast } from 'sonner';

/**
 * Custom hook for scenario operations (export, save, load, import, delete)
 */
export function useScenarioOperations() {
  const { displayError } = useError();
  const { t } = usePreferences();

  /**
   * Formats backend error responses into user-friendly messages
   */
  const formatBackendError = (error: unknown): string => {
    let message = 'Unknown error';
    if (error && typeof error === 'object') {
      const errorObj = error as {
        response?: { data?: unknown };
        message?: string;
      };

      const responseData = errorObj.response?.data as
        | { detail?: unknown; errors?: unknown }
        | undefined;

      // Handle new structured error format: { message: "...", errors: [...] }
      // Check both detail.errors and direct errors at top level
      const detail = responseData?.detail;
      const errors =
        detail && typeof detail === 'object' && 'errors' in detail
          ? detail.errors
          : responseData?.errors;

      if (errors && Array.isArray(errors)) {
        const formattedErrors = errors.map(
          (
            err: { field?: string; message: string; line?: number } | string
          ) => {
            if (typeof err === 'string') return `• ${err}`;
            const fieldInfo = err.field ? `[${err.field}]: ` : '';
            const lineInfo = err.line ? ` (line ${err.line})` : '';
            return `• ${fieldInfo}${err.message}${lineInfo}`;
          }
        );
        return formattedErrors.join('\n');
      }

      // Handle string errors
      if (typeof detail === 'string') {
        return detail;
      }

      // Fallback to error message
      message = errorObj.message || message;
    }
    return message;
  };

  /**
   * Validates scenario content and returns parsed JSON
   * @returns Parsed content if valid, null if invalid
   */
  const validateContent = async (content: string) => {
    if (!content.trim()) {
      displayError(
        t.scenario.error.noContentToProcessTitle,
        t.scenario.error.noContentToProcessDescription
      );
      return null;
    }

    // Validate JSON format
    let parsedContent;
    try {
      parsedContent = JSON.parse(content);
    } catch {
      displayError(
        t.scenario.error.invalidJsonTitle,
        t.scenario.error.invalidJsonDescription
      );
      return null;
    }

    try {
      // Send raw JSON string with formatting to preserve line numbers
      // Use 2-space indentation to match user's editor formatting
      const requestBody = JSON.stringify(
        {
          content: parsedContent,
        },
        null,
        2
      );

      const response = await api.post('/scenarios/validate', requestBody, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const result = response.data;

      // Check if validation failed
      if (!result.valid) {
        // Backend returns errors as an array of objects with field, message, and optional line
        const errors = Array.isArray(result.errors)
          ? result.errors
          : [result.errors].filter(Boolean);

        displayError(
          t.scenario.error.validationFailedTitle,
          errors
            .map((e: { field?: string; message: string; line?: number }) => {
              const fieldInfo = e.field ? `[${e.field}]: ` : '';
              const lineInfo = e.line ? ` (line ${e.line})` : '';
              return `• ${fieldInfo}${e.message}${lineInfo}`;
            })
            .join('\n')
        );
        return null;
      }

      // Log warnings if present (non-blocking)
      if (
        result.warnings &&
        Array.isArray(result.warnings) &&
        result.warnings.length > 0
      ) {
        console.warn(
          'Scenario validation warnings:',
          result.warnings.join('\n')
        );
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
      displayError(t.scenario.error.validationTitle, message);
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
        t.scenario.error.downloadFailedTitle,
        t.scenario.error.downloadFailedDescription
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
      context: LogContext.ScenarioExport,
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
    // Just validate JSON format locally - backend will do full validation
    if (!content.trim()) {
      displayError(
        t.scenario.error.noContentToSaveTitle,
        t.scenario.error.noContentToSaveDescription
      );
      return null;
    }

    let parsedContent;
    try {
      parsedContent = JSON.parse(content);
    } catch {
      displayError(
        t.scenario.error.invalidJsonTitle,
        t.scenario.error.invalidJsonDescription
      );
      return null;
    }

    try {
      const response = await api.post('/scenarios', {
        name: scenarioName,
        content: parsedContent,
        description,
        allow_duplicate_name: false,
      });
      toast.success('Scenario saved successfully!');
      return response.data?.id ?? null;
    } catch (error: unknown) {
      displayError(t.scenario.error.saveFailedTitle, formatBackendError(error));
      return null;
    }
  };

  // Overwrites scenario in backend
  const overwriteScenario = async (
    scenarioId: number,
    content: string,
    scenarioName: string,
    description: string = ''
  ) => {
    // Just validate JSON format locally - backend will do full validation
    if (!content.trim()) {
      displayError(
        t.scenario.error.noContentToSaveTitle,
        t.scenario.error.noContentToSaveDescription
      );
      return null;
    }

    let parsedContent;
    try {
      parsedContent = JSON.parse(content);
    } catch {
      displayError(
        t.scenario.error.invalidJsonTitle,
        t.scenario.error.invalidJsonDescription
      );
      return null;
    }

    try {
      const response = await api.put(`/scenarios/${scenarioId}`, {
        name: scenarioName,
        content: parsedContent,
        description,
      });
      toast.success('Scenario overwritten successfully!');
      return response.data?.id ?? scenarioId;
    } catch (error: unknown) {
      displayError(
        t.scenario.error.overwriteFailedTitle,
        formatBackendError(error)
      );
      return null;
    }
  };

  // Deletes scenario from backend
  const deleteScenario = async (scenarioId: number) => {
    try {
      await api.delete(`/scenarios/${scenarioId}`);
      toast.success('Scenario deleted successfully!');
      log({
        message: `Scenario ${scenarioId} deleted`,
        level: LogLevel.INFO,
      });
      return true;
    } catch (error: unknown) {
      displayError(
        t.scenario.error.deleteFailedTitle,
        formatBackendError(error)
      );
      return false;
    }
  };

  return {
    validateContent,
    downloadJSON,
    exportScenario,
    saveScenario,
    overwriteScenario,
    deleteScenario,
    formatBackendError,
  };
}
