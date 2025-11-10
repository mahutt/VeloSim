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

import { test, expect } from '../fixtures/authenticated-page';

test.describe('Load Scenario Tests', () => {
  test('AT-11.1: Load a Scenario', async ({ authenticatedPage }) => {
    // title of page is visible
    const title = authenticatedPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible({ timeout: 1000 });

    // select scenario card
    const cardcontent = authenticatedPage
      .locator('div.flex.items-center')
      .filter({ hasText: 'Test Scenario 1' });
    await cardcontent.click();
    await authenticatedPage.waitForTimeout(1000);

    // validate fields are not empty
    const scenarioNameInput = authenticatedPage.getByLabel('Scenario name');
    const jsonField = authenticatedPage.getByLabel('Scenario JSON');
    await expect(scenarioNameInput).toHaveValue('Test Scenario 1');
    await expect(jsonField).not.toHaveValue('');

    // validate fields are disabled
    await expect(scenarioNameInput).toBeDisabled();
    await expect(jsonField).toBeDisabled();

    // select edit button
    const editButton = authenticatedPage.getByRole('button', { name: 'Edit' });
    await editButton.click();
    await authenticatedPage.waitForTimeout(500);

    // validate fields are enabled
    await expect(scenarioNameInput).toBeEnabled();
    await expect(jsonField).toBeEnabled();
  });

  test('AT-11.2: Failure to Load Scenario', async ({ authenticatedPage }) => {
    await authenticatedPage.route('**/scenarios?*', (route) => {
      route.abort('failed');
    });

    //await authenticatedPage.reload();
    const dialogTitle = authenticatedPage.getByRole('heading', {
      name: 'Failure loading scenarios',
    });
    await expect(dialogTitle).toBeVisible();
    await authenticatedPage.waitForTimeout(1000);

    const closeButton = authenticatedPage.getByTestId('error-dialog-close');
    await closeButton.click();
    await authenticatedPage.waitForTimeout(500);

    // title of page is visible
    const title = authenticatedPage.locator('h1:has-text("Scenario Editor")');
    await expect(title).toBeVisible();
  });
});
