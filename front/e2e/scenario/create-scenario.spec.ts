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

import { test, expect } from '../fixtures/scenario-page';

const invalidScenario = `{
  "start_time": "2025-11-06T08:00:00Z",
  "end_time": "2025-11-06T17:00:00Z",
  "stations": [
    {
      "station_id": 1,
      "station_name": "Station 1",
      "station_position": [
        -74.006,
        40.7128
      ]
    }
  ],
  "resources": [
    {
      "resource_id": 1,
      "resource_position": [
        -74.006,
        40.7128
      ]
    }
  ];
  "initial_tasks": [
    {
      "id": "t1",
      "station_id": 1
    }
  ]
}`;

test.describe('Create Scenario Tests', () => {
  test('AT-9.1: Begin Creation of a New Scenario', async ({ scenarioPage }) => {
    // title of page is visible
    const title = scenarioPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });
    await scenarioPage.waitForTimeout(1500);

    // fill scenario text area
    const scenarioTextarea = scenarioPage.getByLabel('Scenario JSON');
    expect(scenarioTextarea).toHaveValue('');
    const sampleText = `{
        "test": "Can add JSON here",
    }`;
    await scenarioTextarea.fill(sampleText);
    await scenarioPage.waitForTimeout(1000);
  });

  test('AT-9.3: Creation of Invalid Scenario', async ({ scenarioPage }) => {
    // title of page is visible
    const title = scenarioPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });

    // fill scenario text area with invalid json
    const scenarioTextarea = scenarioPage.getByLabel('Scenario JSON');
    await scenarioTextarea.fill(invalidScenario);
    await scenarioPage.waitForTimeout(500);

    const startButton = scenarioPage.getByRole('button', {
      name: 'Start Simulation',
    });
    startButton.click();
    await scenarioPage.waitForTimeout(500);

    // error message is displayed
    const errorTitle = scenarioPage.getByRole('heading', {
      name: 'Invalid Scenario',
    });
    await expect(errorTitle).toBeVisible();

    // close error dialog
    const closeButton = scenarioPage.getByTestId('error-dialog-close');
    await closeButton.click();
    await scenarioPage.waitForTimeout(1000);
  });

  /*
  // commented out for now until performance is improved on initializing sim
  test('AT-9.2: Start Simulation from Created Scenario', async ({ scenarioPage }) => {
    // title of page is visible
    const title = scenarioPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });

    // fill scenario text area
    const scenarioTextarea = scenarioPage.getByLabel('Scenario JSON');
    await scenarioTextarea.fill(sampleScenario);
    await scenarioPage.waitForTimeout(500);

    const startButton = scenarioPage.getByRole('button', {name: 'Start Simulation'});
    startButton.click();
    await scenarioPage.waitForURL((url) => url.pathname.includes('/simulation'));
    await scenarioPage.waitForTimeout(500);
  });*/
});
