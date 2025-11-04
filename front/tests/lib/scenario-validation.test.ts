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

import { describe, it, expect } from 'vitest';
import {
  validateScenario,
  formatValidationResults,
  type ScenarioFormat,
} from '~/lib/scenario-validation';

describe('validateScenario', () => {
  describe('Basic validation', () => {
    it('validates a complete valid scenario', () => {
      const scenario: ScenarioFormat = {
        scenario_title: 'Morning Simulation',
        start_time: '08:00',
        end_time: '12:00',
        resources: [{ id: 'r1', type: 'bike' }],
        stations: [{ id: 's1', name: 'Station 1' }],
        initial_tasks: [{ id: 't1', station_id: 's1' }],
        scheduled_tasks: [{ id: 't2', station_id: 's1', time: '10:00' }],
      };

      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('rejects non-object input', () => {
      const result = validateScenario('not an object');

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Scenario must be a valid JSON object');
    });

    it('rejects null input', () => {
      const result = validateScenario(null);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Scenario must be a valid JSON object');
    });

    it('accepts empty object with warnings', () => {
      const result = validateScenario({});

      expect(result.valid).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
    });
  });

  describe('scenario_title validation', () => {
    it('accepts valid scenario title', () => {
      const scenario = { scenario_title: 'Test Scenario' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('warns on missing scenario_title', () => {
      const scenario = {};
      const result = validateScenario(scenario);

      expect(result.warnings).toContain('scenario_title is not defined');
    });

    it('warns on empty scenario_title', () => {
      const scenario = { scenario_title: '   ' };
      const result = validateScenario(scenario);

      expect(result.warnings).toContain('scenario_title is empty');
    });

    it('rejects non-string scenario_title', () => {
      const scenario = { scenario_title: 123 };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('scenario_title must be a string');
    });
  });

  describe('Time validation', () => {
    it('accepts valid time formats', () => {
      const scenario = {
        start_time: '08:00',
        end_time: '17:30',
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('rejects invalid start_time format', () => {
      const scenario = { start_time: '8:00' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'start_time must be in HH:MM format (e.g., "08:00")'
      );
    });

    it('rejects invalid end_time format', () => {
      const scenario = { end_time: '25:00' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'end_time must be in HH:MM format (e.g., "12:00")'
      );
    });

    it('rejects end_time before start_time', () => {
      const scenario = {
        start_time: '12:00',
        end_time: '08:00',
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('end_time must be after start_time');
    });

    it('accepts end_time equal to start_time (edge case)', () => {
      const scenario = {
        start_time: '12:00',
        end_time: '12:00',
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('end_time must be after start_time');
    });

    it('rejects non-string time values', () => {
      const scenario = {
        start_time: 800,
        end_time: 1200,
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('start_time must be a string');
      expect(result.errors).toContain('end_time must be a string');
    });
  });

  describe('Resources validation', () => {
    it('accepts valid resources array', () => {
      const scenario = {
        resources: [
          { id: 'r1', type: 'bike' },
          { id: 'r2', type: 'ebike' },
        ],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
    });

    it('rejects non-array resources', () => {
      const scenario = { resources: 'not an array' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('resources must be an array');
    });

    it('rejects resources without id', () => {
      const scenario = {
        resources: [{ type: 'bike' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('resources[0] must have an id field');
    });

    it('warns on resources without type', () => {
      const scenario = {
        resources: [{ id: 'r1' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain('resources[0] is missing a type field');
    });
  });

  describe('Stations validation', () => {
    it('accepts valid stations array', () => {
      const scenario = {
        stations: [
          { id: 's1', name: 'Station 1' },
          { id: 's2', name: 'Station 2' },
        ],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
    });

    it('rejects non-array stations', () => {
      const scenario = { stations: 'not an array' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('stations must be an array');
    });

    it('rejects stations without id', () => {
      const scenario = {
        stations: [{ name: 'Station' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('stations[0] must have an id field');
    });

    it('warns on empty stations array', () => {
      const scenario = { stations: [] };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain('stations array is empty');
    });

    it('warns on missing stations', () => {
      const scenario = {};
      const result = validateScenario(scenario);

      expect(result.warnings).toContain('No stations defined');
    });
  });

  describe('Initial tasks validation', () => {
    it('accepts valid initial_tasks', () => {
      const scenario = {
        stations: [{ id: 's1' }],
        initial_tasks: [{ id: 't1', station_id: 's1' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
    });

    it('rejects non-array initial_tasks', () => {
      const scenario = { initial_tasks: 'not an array' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('initial_tasks must be an array');
    });

    it('rejects tasks without id', () => {
      const scenario = {
        initial_tasks: [{ station_id: 's1' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('initial_tasks[0] must have an id field');
    });

    it('rejects tasks without station_id', () => {
      const scenario = {
        initial_tasks: [{ id: 't1' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'initial_tasks[0] must have a station_id field'
      );
    });

    it('warns on unknown station_id reference', () => {
      const scenario = {
        stations: [{ id: 's1' }],
        initial_tasks: [{ id: 't1', station_id: 's999' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain(
        'initial_tasks[0] references unknown station_id: s999'
      );
    });
  });

  describe('Scheduled tasks validation', () => {
    it('accepts valid scheduled_tasks', () => {
      const scenario = {
        start_time: '08:00',
        end_time: '12:00',
        stations: [{ id: 's1' }],
        scheduled_tasks: [{ id: 't1', station_id: 's1', time: '10:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
    });

    it('rejects non-array scheduled_tasks', () => {
      const scenario = { scheduled_tasks: 'not an array' };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('scheduled_tasks must be an array');
    });

    it('rejects tasks without id', () => {
      const scenario = {
        scheduled_tasks: [{ station_id: 's1', time: '10:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'scheduled_tasks[0] must have an id field'
      );
    });

    it('rejects tasks without station_id', () => {
      const scenario = {
        scheduled_tasks: [{ id: 't1', time: '10:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'scheduled_tasks[0] must have a station_id field'
      );
    });

    it('rejects tasks without time', () => {
      const scenario = {
        scheduled_tasks: [{ id: 't1', station_id: 's1' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'scheduled_tasks[0] must have a time field'
      );
    });

    it('rejects tasks with invalid time format', () => {
      const scenario = {
        scheduled_tasks: [{ id: 't1', station_id: 's1', time: '10:00:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        'scheduled_tasks[0] time must be in HH:MM format'
      );
    });

    it('warns on task time before start_time', () => {
      const scenario = {
        start_time: '10:00',
        scheduled_tasks: [{ id: 't1', station_id: 's1', time: '08:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain(
        'scheduled_tasks[0] time (08:00) is before start_time (10:00)'
      );
    });

    it('warns on task time after end_time', () => {
      const scenario = {
        end_time: '10:00',
        scheduled_tasks: [{ id: 't1', station_id: 's1', time: '12:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain(
        'scheduled_tasks[0] time (12:00) is after end_time (10:00)'
      );
    });

    it('warns on unknown station_id reference', () => {
      const scenario = {
        stations: [{ id: 's1' }],
        scheduled_tasks: [{ id: 't1', station_id: 's999', time: '10:00' }],
      };
      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.warnings).toContain(
        'scheduled_tasks[0] references unknown station_id: s999'
      );
    });
  });

  describe('Complex scenarios', () => {
    it('validates the Morning Simulation scenario', () => {
      const scenario: ScenarioFormat = {
        scenario_title: 'Morning Simulation Run',
        start_time: '08:00',
        end_time: '12:00',
        resources: [
          { id: 'bike-001', type: 'bike' },
          { id: 'bike-002', type: 'bike' },
        ],
        stations: [
          { id: 's1', name: 'Station 1' },
          { id: 's2', name: 'Station 2' },
        ],
        initial_tasks: [
          { id: 't1', station_id: 's1' },
          { id: 't2', station_id: 's2' },
        ],
        scheduled_tasks: [
          { id: 't3', station_id: 's1', time: '09:30' },
          { id: 't4', station_id: 's2', time: '10:15' },
        ],
      };

      const result = validateScenario(scenario);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('handles multiple validation errors', () => {
      const scenario = {
        scenario_title: 123,
        start_time: 'invalid',
        end_time: '25:00',
        resources: 'not an array',
        stations: [{ name: 'missing id' }],
        initial_tasks: [{ id: 't1' }],
        scheduled_tasks: 'not an array',
      };

      const result = validateScenario(scenario);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(5);
    });
  });
});

describe('formatValidationResults', () => {
  it('formats valid results with no errors or warnings', () => {
    const result = {
      valid: true,
      errors: [],
      warnings: [],
    };

    const formatted = formatValidationResults(result);

    expect(formatted).toBe('');
  });

  it('formats invalid results with errors', () => {
    const result = {
      valid: false,
      errors: ['Error 1', 'Error 2'],
      warnings: [],
    };

    const formatted = formatValidationResults(result);

    expect(formatted).toContain('Errors:');
    expect(formatted).toContain(': Error 1');
    expect(formatted).toContain(': Error 2');
  });

  it('formats results with warnings', () => {
    const result = {
      valid: true,
      errors: [],
      warnings: ['Warning 1', 'Warning 2'],
    };

    const formatted = formatValidationResults(result);

    expect(formatted).toContain('Warnings:');
    expect(formatted).toContain(': Warning 1');
    expect(formatted).toContain(': Warning 2');
  });

  it('formats results with both errors and warnings', () => {
    const result = {
      valid: false,
      errors: ['Critical error'],
      warnings: ['Minor warning'],
    };

    const formatted = formatValidationResults(result);

    expect(formatted).toContain('Errors:');
    expect(formatted).toContain(': Critical error');
    expect(formatted).toContain('Warnings:');
    expect(formatted).toContain(': Minor warning');
  });
});
