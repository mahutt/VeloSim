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

import { test as base, type Page } from '@playwright/test';
import { TEST_CONFIG } from '../config/test-config';

type AuthFixtures = {
  scenarioPage: Page;
};

export const test = base.extend<AuthFixtures>({
  scenarioPage: async ({ page }, use) => {
    await page.goto('/login');
    await page.fill('#form-login-username', TEST_CONFIG.credentials.username);
    await page.fill('#form-login-password', TEST_CONFIG.credentials.password);
    await page.click('button[type="submit"]');
    await page.waitForURL('/');
    await page.waitForTimeout(500);

    const cardcontent = page
      .locator('div.flex.items-center')
      .filter({ hasText: 'E2E Scenario' });
    const count = await cardcontent.count();
    if (count > 0) {
      const deleteButton = cardcontent.getByRole('button');
      await deleteButton.click();
      await page.waitForTimeout(500);

      const dialogDelete = page.getByRole('button', { name: 'Delete' });
      await dialogDelete.click();
      await page.waitForTimeout(500);
      // reload page to ensure we restart tests fresh
      await page.goto('/');
    }

    await use(page);
  },
});

export { expect } from '@playwright/test';
