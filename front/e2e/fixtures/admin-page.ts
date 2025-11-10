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

import { test as base, type Page, type Locator } from '@playwright/test';
import { TEST_CONFIG } from '../config/test-config';

type AdminFixtures = {
  adminPage: Page;
  testUserHelper: TestUserHelper;
};

interface TestUserHelper {
  createUser: (
    username: string,
    password: string,
    isAdmin?: boolean
  ) => Promise<void>;
  deleteUser: (username: string) => Promise<void>;
  getUserRow: (username: string) => Promise<Locator>;
}

/**
 * Extended test fixture for admin user management tests
 * Provides authenticated admin session and user management utilities
 */
export const test = base.extend<AdminFixtures>({
  adminPage: async ({ page }, use) => {
    // Login as admin
    await page.goto('/login');
    await page.fill('#form-login-username', TEST_CONFIG.credentials.username);
    await page.fill('#form-login-password', TEST_CONFIG.credentials.password);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'));

    // Navigate to users page
    await page.goto('/users');
    await page.waitForLoadState('domcontentloaded');

    await use(page);
  },

  testUserHelper: async ({ adminPage }, use) => {
    const helper: TestUserHelper = {
      createUser: async (
        username: string,
        password: string,
        isAdmin = false
      ) => {
        await adminPage.goto('/users');
        await adminPage.waitForLoadState('domcontentloaded');

        // Click new user button
        await adminPage.getByRole('button', { name: /new user/i }).click();

        // Wait for dialog
        await adminPage.waitForSelector('#form-new-user-username', {
          timeout: 5000,
        });

        // Fill form
        await adminPage.fill('#form-new-user-username', username);
        await adminPage.fill('#form-new-user-password', password);

        // Set admin checkbox if needed
        if (isAdmin) {
          await adminPage.click('#form-new-user-is-admin');
        }

        // Submit
        await adminPage.click('button[type="submit"]');

        // Wait for success message
        await adminPage.waitForSelector('text=/user created successfully/i', {
          timeout: 5000,
        });

        // Wait a bit for UI to update
        await adminPage.waitForTimeout(1000);
      },

      deleteUser: async (username: string) => {
        // Note: If delete functionality doesn't exist in UI,
        // this would need to use API directly
        await adminPage.goto('/users');
        await adminPage.waitForLoadState('networkidle');

        // Search for user
        await adminPage.fill('input[placeholder*="Filter"]', username);
        await adminPage.waitForTimeout(500);

        const userRow = adminPage.locator(`tbody tr:has-text("${username}")`);
        if ((await userRow.count()) > 0) {
          // If there's a delete option in the actions menu
          const actionsButton = userRow.locator('[data-testid="user-actions"]');
          await actionsButton.click();

          const deleteOption = adminPage.locator('text=/delete/i');
          if (
            await deleteOption.isVisible({ timeout: 1000 }).catch(() => false)
          ) {
            await deleteOption.click();
          }
        }
      },

      getUserRow: async (username: string) => {
        await adminPage.goto('/users');
        await adminPage.waitForLoadState('networkidle');

        // Search for user
        await adminPage.fill('input[placeholder*="Filter"]', username);
        await adminPage.waitForTimeout(500);

        return adminPage.locator(`tbody tr:has-text("${username}")`).first();
      },
    };

    await use(helper);
  },
});

export { expect } from '@playwright/test';
