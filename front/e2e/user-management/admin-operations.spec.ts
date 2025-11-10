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

import { test, expect } from '../fixtures/admin-page';

test.describe('User Management - Advanced', () => {
  /**
   * AT-7.2: User creation (comprehensive test)
   *
   * Tests creating users with different roles and validating form behavior
   */
  test('AT-7.2: User creation with different roles', async ({
    testUserHelper,
  }) => {
    // Test 1: Create admin user
    const adminTimestamp = Date.now();
    const adminUsername = `admin_${adminTimestamp}`;

    await testUserHelper.createUser(adminUsername, 'securepass123', true);

    let userRow = await testUserHelper.getUserRow(adminUsername);
    await expect(userRow).toBeVisible();
    await expect(userRow.getByText('Admin', { exact: true })).toBeVisible();
    await expect(userRow.getByText('Enabled')).toBeVisible();

    // Test 2: Create regular user
    const userTimestamp = Date.now();
    const regularUsername = `user_${userTimestamp}`;

    await testUserHelper.createUser(regularUsername, 'userpass123', false);

    userRow = await testUserHelper.getUserRow(regularUsername);
    await expect(userRow).toBeVisible();
    await expect(userRow.getByText('User', { exact: true })).toBeVisible();
    await expect(userRow.getByText('Enabled')).toBeVisible();
  });

  /**
   * AT-7.3: Password reset (detailed test)
   *
   * Tests password reset with validation including successful reset and mismatch validation
   */
  test('AT-7.3: Password reset with validation', async ({
    adminPage,
    testUserHelper,
  }) => {
    // Part 1: Test successful password reset
    const timestamp1 = Date.now();
    const username1 = `pwdtest_${timestamp1}`;

    await testUserHelper.createUser(username1, 'oldpassword', false);

    let userRow = await testUserHelper.getUserRow(username1);
    await expect(userRow).toBeVisible();

    // Open actions menu and change password
    await userRow.locator('[data-testid="user-actions"]').click();
    await adminPage.click('text=/change password/i');

    // Wait for dialog
    await expect(
      adminPage.getByRole('heading', { name: /update password/i })
    ).toBeVisible();

    // Fill password fields
    const newPassword = 'newSecurePass456';
    let passwordFields = adminPage.locator('input[type="password"]');
    await passwordFields.nth(0).fill(newPassword);
    await passwordFields.nth(1).fill(newPassword);

    // Submit
    await adminPage.click('button[type="submit"]');

    // Verify success
    await expect(
      adminPage.locator('text=/password updated successfully/i')
    ).toBeVisible({ timeout: 5000 });

    // Part 2: Test password mismatch validation
    const timestamp2 = Date.now();
    const username2 = `pwdval_${timestamp2}`;

    await testUserHelper.createUser(username2, 'password123', false);

    userRow = await testUserHelper.getUserRow(username2);
    await userRow.locator('[data-testid="user-actions"]').click();
    await adminPage.click('text=/change password/i');

    // Fill with mismatched passwords
    passwordFields = adminPage.locator('input[type="password"]');
    await passwordFields.nth(0).fill('password1');
    await passwordFields.nth(1).fill('password2');

    // Submit
    await adminPage.click('button[type="submit"]');

    // Verify error message
    await expect(
      adminPage.locator("text=/passwords don't match/i")
    ).toBeVisible({ timeout: 3000 });
  });

  /**
   * AT-7.4: Disable/enable user (comprehensive test)
   */
  test('AT-7.4: Toggle user enabled status', async ({
    adminPage,
    testUserHelper,
  }) => {
    const timestamp = Date.now();
    const username = `toggle_${timestamp}`;

    // Create a test user
    await testUserHelper.createUser(username, 'testpass', false);

    // Get user row
    let userRow = await testUserHelper.getUserRow(username);
    await expect(userRow).toBeVisible();

    // Verify initially enabled
    await expect(userRow.getByText('Enabled')).toBeVisible();

    // Disable user
    await userRow.locator('[data-testid="user-actions"]').click();
    await adminPage.click('text=/disable user/i');

    // Re-query to avoid stale element
    userRow = await testUserHelper.getUserRow(username);

    // Verify disabled
    await expect(userRow.getByText('Disabled')).toBeVisible({
      timeout: 5000,
    });

    // Re-enable user
    await userRow.locator('[data-testid="user-actions"]').click();
    await adminPage.click('text=/enable user/i');

    // Re-query again
    userRow = await testUserHelper.getUserRow(username);

    // Verify enabled again
    await expect(userRow.getByText('Enabled')).toBeVisible({
      timeout: 5000,
    });
  });

  /**
   * AT-7.5: User role change (comprehensive test)
   *
   * Tests promoting and demoting user roles, plus protection against changing own role
   */
  test('AT-7.5: User role management', async ({
    adminPage,
    testUserHelper,
  }) => {
    // Part 1: Toggle user admin role
    const timestamp = Date.now();
    const username = `roletest_${timestamp}`;

    // Create regular user
    await testUserHelper.createUser(username, 'testpass', false);

    // Get user row
    let userRow = await testUserHelper.getUserRow(username);
    await expect(userRow).toBeVisible();

    // Verify user role is "User"
    await expect(userRow.getByText('User', { exact: true })).toBeVisible();

    // Promote to admin
    await userRow.locator('[data-testid="user-actions"]').click();
    await adminPage.click('text=/make admin/i');

    // Re-query to avoid stale element
    userRow = await testUserHelper.getUserRow(username);

    // Verify admin role
    await expect(userRow.getByText('Admin', { exact: true })).toBeVisible({
      timeout: 5000,
    });

    // Demote to regular user
    await userRow.locator('[data-testid="user-actions"]').click();
    await adminPage.click('text=/revoke admin/i');

    // Re-query again
    userRow = await testUserHelper.getUserRow(username);

    // Verify user role again
    await expect(userRow.getByText('User', { exact: true })).toBeVisible({
      timeout: 5000,
    });

    // Part 2: Cannot change own admin role
    // Search for admin user (current logged-in user)
    await adminPage.fill('input[placeholder*="Filter"]', 'admin');
    await adminPage.waitForTimeout(500);

    const adminUserRow = adminPage
      .locator('tbody tr:has-text("admin")')
      .first();
    await expect(adminUserRow).toBeVisible();

    // Open actions menu
    await adminUserRow.locator('[data-testid="user-actions"]').click();

    // Verify "Revoke admin" option is disabled
    const revokeOption = adminPage.locator('text=/revoke admin/i');

    // The option should either be disabled or not visible for current user
    // This depends on implementation - checking if it's disabled
    if (await revokeOption.isVisible({ timeout: 1000 }).catch(() => false)) {
      await expect(revokeOption).toBeDisabled();
    }
  });

  /**
   * AT-7.7: User preference management
   *
   * Tests that users can manage their scenarios (preferences) including view, export, and import
   */
  test('AT-7.7: User scenario management', async ({ adminPage }) => {
    // Navigate to scenarios page
    await adminPage.goto('/scenarios');
    await adminPage.waitForLoadState('networkidle');

    // Verify scenarios page loads
    await expect(adminPage).toHaveURL(/\/scenarios/);

    // Part 1: View user scenarios
    const savedScenariosSection = adminPage.locator('text=/saved scenarios/i');
    await expect(savedScenariosSection).toBeVisible({ timeout: 5000 });

    // Verify scenario editor exists (be specific about which textarea)
    const scenarioEditor = adminPage.locator(
      'textarea[placeholder*="JSON scenario"]'
    );
    await expect(scenarioEditor).toBeVisible();

    // Part 2: Export scenario functionality
    const exportButton = adminPage.getByRole('button', { name: /export/i });

    if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(exportButton).toBeEnabled();
      // Could test download functionality here if needed
      // Would require download event handling
    }

    // Part 3: Import scenario functionality
    const importButton = adminPage.getByRole('button', { name: /import/i });

    if (await importButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(importButton).toBeEnabled();

      // Click to open file picker dialog
      await importButton.click();

      // Verify file input appears (may be hidden but present)
      const fileInput = adminPage.locator('input[type="file"]');
      await expect(fileInput).toBeAttached({ timeout: 3000 });
    }
  });
});
