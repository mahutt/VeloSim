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
  authenticatedPage: Page;
};

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Navigate to login page
    await page.goto('/login');

    // Fill in credentials
    await page.fill('#form-login-username', TEST_CONFIG.credentials.username);
    await page.fill('#form-login-password', TEST_CONFIG.credentials.password);

    // Submit login form
    await page.click('button[type="submit"]');

    // Wait for navigation away from login page
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 10000,
    });

    // Add a small delay to ensure cookies/tokens are set
    await page.waitForTimeout(1000);

    // Verify authentication by checking for auth token or user info
    // This helps catch auth issues early
    await page.waitForLoadState('networkidle');

    await use(page);
  },
});

export { expect } from '@playwright/test';
