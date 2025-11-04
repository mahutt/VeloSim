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

export interface ScenarioTask {
  id: string;
  station_id: string;
  time?: string;
}

export interface ScenarioResource {
  id: string;
  type: string;
  capacity?: number;
  [key: string]: unknown;
}

export interface ScenarioStation {
  id: string;
  name?: string;
  location?: {
    lat: number;
    lng: number;
  };
  [key: string]: unknown;
}

export interface ScenarioFormat {
  scenario_title?: string;
  start_time?: string;
  end_time?: string;
  resources?: ScenarioResource[];
  stations?: ScenarioStation[];
  initial_tasks?: ScenarioTask[];
  scheduled_tasks?: ScenarioTask[];
  [key: string]: unknown;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validates time format (HH:MM)
 */
function isValidTimeFormat(time: string): boolean {
  const timeRegex = /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/;
  return timeRegex.test(time);
}

/**
 * Validates that end time is after start time
 */
function isEndTimeAfterStartTime(startTime: string, endTime: string): boolean {
  const [startHour, startMin] = startTime.split(':').map(Number);
  const [endHour, endMin] = endTime.split(':').map(Number);
  return endHour > startHour || (endHour === startHour && endMin > startMin);
}

/**
 * Validates a scenario object structure and content
 *
 * TODO: Update validation rules based on backend import requirements.
 * Current validation is permissive (mostly warnings) to allow flexibility during development.
 * Once backend API contract is defined, update this to match required fields for import.
 */
export function validateScenario(scenarioData: unknown): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check if data is an object
  if (!scenarioData || typeof scenarioData !== 'object') {
    return {
      valid: false,
      errors: ['Scenario must be a valid JSON object'],
      warnings: [],
    };
  }

  const scenario = scenarioData as ScenarioFormat;

  // Validate scenario_title
  if (scenario.scenario_title !== undefined) {
    if (typeof scenario.scenario_title !== 'string') {
      errors.push('scenario_title must be a string');
    } else if (scenario.scenario_title.trim().length === 0) {
      warnings.push('scenario_title is empty');
    }
  } else {
    warnings.push('scenario_title is not defined');
  }

  // Validate start_time
  if (scenario.start_time !== undefined) {
    if (typeof scenario.start_time !== 'string') {
      errors.push('start_time must be a string');
    } else if (!isValidTimeFormat(scenario.start_time)) {
      errors.push('start_time must be in HH:MM format (e.g., "08:00")');
    }
  }

  // Validate end_time
  if (scenario.end_time !== undefined) {
    if (typeof scenario.end_time !== 'string') {
      errors.push('end_time must be a string');
    } else if (!isValidTimeFormat(scenario.end_time)) {
      errors.push('end_time must be in HH:MM format (e.g., "12:00")');
    } else if (
      scenario.start_time &&
      isValidTimeFormat(scenario.start_time) &&
      !isEndTimeAfterStartTime(scenario.start_time, scenario.end_time)
    ) {
      errors.push('end_time must be after start_time');
    }
  }

  // Validate resources array
  if (scenario.resources !== undefined) {
    if (!Array.isArray(scenario.resources)) {
      errors.push('resources must be an array');
    } else {
      scenario.resources.forEach((resource, index) => {
        if (!resource.id) {
          errors.push(`resources[${index}] must have an id field`);
        }
        if (!resource.type) {
          warnings.push(`resources[${index}] is missing a type field`);
        }
      });
    }
  }

  // Validate stations array
  if (scenario.stations !== undefined) {
    if (!Array.isArray(scenario.stations)) {
      errors.push('stations must be an array');
    } else {
      scenario.stations.forEach((station, index) => {
        if (!station.id) {
          errors.push(`stations[${index}] must have an id field`);
        }
      });

      if (scenario.stations.length === 0) {
        warnings.push('stations array is empty');
      }
    }
  } else {
    warnings.push('No stations defined');
  }

  // Validate initial_tasks array
  if (scenario.initial_tasks !== undefined) {
    if (!Array.isArray(scenario.initial_tasks)) {
      errors.push('initial_tasks must be an array');
    } else {
      const stationIds = new Set(scenario.stations?.map((s) => s.id) || []);

      scenario.initial_tasks.forEach((task, index) => {
        if (!task.id) {
          errors.push(`initial_tasks[${index}] must have an id field`);
        }
        if (!task.station_id) {
          errors.push(`initial_tasks[${index}] must have a station_id field`);
        } else if (stationIds.size > 0 && !stationIds.has(task.station_id)) {
          warnings.push(
            `initial_tasks[${index}] references unknown station_id: ${task.station_id}`
          );
        }
      });
    }
  }

  // Validate scheduled_tasks array
  if (scenario.scheduled_tasks !== undefined) {
    if (!Array.isArray(scenario.scheduled_tasks)) {
      errors.push('scheduled_tasks must be an array');
    } else {
      const stationIds = new Set(scenario.stations?.map((s) => s.id) || []);

      scenario.scheduled_tasks.forEach((task, index) => {
        if (!task.id) {
          errors.push(`scheduled_tasks[${index}] must have an id field`);
        }
        if (!task.station_id) {
          errors.push(`scheduled_tasks[${index}] must have a station_id field`);
        } else if (stationIds.size > 0 && !stationIds.has(task.station_id)) {
          warnings.push(
            `scheduled_tasks[${index}] references unknown station_id: ${task.station_id}`
          );
        }
        if (!task.time) {
          errors.push(`scheduled_tasks[${index}] must have a time field`);
        } else if (!isValidTimeFormat(task.time)) {
          errors.push(`scheduled_tasks[${index}] time must be in HH:MM format`);
        } else if (
          scenario.start_time &&
          isValidTimeFormat(scenario.start_time) &&
          !isEndTimeAfterStartTime(scenario.start_time, task.time)
        ) {
          warnings.push(
            `scheduled_tasks[${index}] time (${task.time}) is before start_time (${scenario.start_time})`
          );
        } else if (
          scenario.end_time &&
          isValidTimeFormat(scenario.end_time) &&
          !isEndTimeAfterStartTime(task.time, scenario.end_time)
        ) {
          warnings.push(
            `scheduled_tasks[${index}] time (${task.time}) is after end_time (${scenario.end_time})`
          );
        }
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Formats validation results as a human-readable string
 */
export function formatValidationResults(result: ValidationResult): string {
  const lines: string[] = [];

  if (result.errors.length > 0) {
    lines.push('\nErrors:');
    result.errors.forEach((error) => {
      lines.push(`  : ${error}`);
    });
  }

  if (result.warnings.length > 0) {
    lines.push('\nWarnings:');
    result.warnings.forEach((warning) => {
      lines.push(`  : ${warning}`);
    });
  }

  return lines.join('\n');
}
