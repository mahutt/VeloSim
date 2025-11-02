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

import { test, expect } from '@playwright/test';
import { TEST_CONFIG } from '../config/test-config';

test.describe('Login', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login form with logo', async ({ page }) => {
    await expect(page.locator('img[alt="VeloSim Logo"]')).toBeVisible();
    // check form fields exist
    await expect(page.locator('#form-login-username')).toBeVisible();
    await expect(page.locator('#form-login-password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.click('button[type="submit"]');
    // wait for validation errors
    await expect(
      page.locator('text=Username must be at least 1 character')
    ).toBeVisible();
    await expect(
      page.locator('text=Password must be at least 1 character')
    ).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.fill('#form-login-username', TEST_CONFIG.credentials.username);
    await page.fill('#form-login-password', TEST_CONFIG.credentials.password);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 5000,
    });
  });
  test('should show error alert on invalid credentials', async ({ page }) => {
    // fill with invalid credentials
    await page.fill('#form-login-username', 'wronguser');
    await page.fill('#form-login-password', 'wrongpass');
    await page.click('button[type="submit"]');
    await expect(page.locator('[role="alert"]')).toBeVisible();
  });
});
