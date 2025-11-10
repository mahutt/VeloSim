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

const sampleScenario = `{
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
  ],
  "initial_tasks": [
    {
      "id": "t1",
      "station_id": 1
    }
  ],
  "scheduled_tasks": [
    {
      "id": "t2",
      "station_id": 1,
      "time": 1800
    },
    {
      "id": "t3",
      "station_id": 1,
      "time": 3600
    }
  ]
}`;

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

test.describe('Save Scenario Tests', () => {
  test('AT-10.1: Save a Scenario', async ({ scenarioPage }) => {
    // title of page is visible
    const title = scenarioPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });

    // fill scenario text area
    const scenarioTextarea = scenarioPage.getByLabel('Scenario JSON');
    await scenarioTextarea.fill(sampleScenario);

    // selecting save opens a name dialog
    const saveButton = scenarioPage.getByRole('button', { name: 'Save' });
    await expect(saveButton).toBeVisible();
    await saveButton.click();
    await scenarioPage.waitForTimeout(500);

    const dialogTitle = scenarioPage.getByRole('heading', {
      name: 'Scenario Name Required',
    });
    await expect(dialogTitle).toBeVisible();

    // enter scenario name and confirm
    const nameInput = scenarioPage.getByRole('textbox', {
      name: 'Scenario Name',
    });
    await nameInput.fill('E2E Scenario');
    const continueButton = scenarioPage.getByRole('button', {
      name: 'Continue',
    });
    await continueButton.click();
    await scenarioPage.waitForTimeout(500);

    // confirm that E2E Scenario is visible
    await expect(
      scenarioPage.getByText('E2E Scenario', { exact: true })
    ).toBeVisible();
  });

  test('AT-10.2: Fail to Save Scenario', async ({ scenarioPage }) => {
    // title of page is visible
    const title = scenarioPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });

    // selecting save opens a name dialog
    const saveButton = scenarioPage.getByRole('button', { name: 'Save' });
    await expect(saveButton).toBeVisible();
    await saveButton.click();
    await scenarioPage.waitForTimeout(500);
    const dialogTitle = scenarioPage.getByRole('heading', {
      name: 'Scenario Name Required',
    });
    await expect(dialogTitle).toBeVisible();

    // enter scenario name and confirm
    const nameInput = scenarioPage.getByRole('textbox', {
      name: 'Scenario Name',
    });
    await nameInput.fill('No JSON Scenario');
    const continueButton = scenarioPage.getByRole('button', {
      name: 'Continue',
    });
    await continueButton.click();
    await scenarioPage.waitForTimeout(1000);

    // no content error message displayed
    const errorTitle = scenarioPage.getByRole('heading', {
      name: 'No content to save',
    });
    const errorMsg = scenarioPage.getByText('Please enter a scenario first');
    await expect(errorTitle).toBeVisible();
    await expect(errorMsg).toBeVisible();

    // close error dialog
    const closeButton = scenarioPage.getByTestId('error-dialog-close');
    await closeButton.click();
    await scenarioPage.waitForTimeout(1000);

    const cardContent = scenarioPage
      .locator('div.text-sm.font-semibold.truncate')
      .filter({ hasText: 'No JSON Scenario' });
    await expect(cardContent).not.toBeVisible();
  });

  test('AT-10.3: Fail to Save Invalid Scenario', async ({ scenarioPage }) => {
    // title of page is visible
    const title = scenarioPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });

    // fill scenario text area with invalid json
    const scenarioTextarea = scenarioPage.getByLabel('Scenario JSON');
    await scenarioTextarea.fill(invalidScenario);

    // selecting save opens a name dialog
    const saveButton = scenarioPage.getByRole('button', { name: 'Save' });
    await expect(saveButton).toBeVisible();
    await saveButton.click();
    await scenarioPage.waitForTimeout(500);

    // enter scenario name and confirm
    const nameInput = scenarioPage.getByRole('textbox', {
      name: 'Scenario Name',
    });
    await nameInput.fill('Bad JSON  Scenario');
    const continueButton = scenarioPage.getByRole('button', {
      name: 'Continue',
    });
    await continueButton.click();
    await scenarioPage.waitForTimeout(500);

    // results in error message
    const errorTitle = scenarioPage.getByRole('heading', {
      name: 'Invalid JSON format',
    });
    await expect(errorTitle).toBeVisible();

    // close error dialog
    const closeButton = scenarioPage.getByTestId('error-dialog-close');
    await closeButton.click();
    await scenarioPage.waitForTimeout(1000);

    const cardContent = scenarioPage
      .locator('div.text-sm.font-semibold.truncate')
      .filter({ hasText: 'Bad JSON  Scenario' });
    await expect(cardContent).not.toBeVisible();
  });
});
