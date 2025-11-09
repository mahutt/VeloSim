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
import type { Page } from '@playwright/test';

async function waitForCanvasChange(
  page: Page,
  canvasSelector: string = 'canvas',
  timeout: number = 5000
) {
  const locator = page.locator(canvasSelector).first();
  const prev = await locator.evaluate((el: HTMLElement | SVGElement | null) => {
    try {
      const c = el as unknown as HTMLCanvasElement | null;
      return c ? c.toDataURL() : '';
    } catch {
      return '';
    }
  });

  await page.waitForFunction(
    (args: { sel: string; prevData: string }) => {
      const { sel, prevData } = args;
      const c = document.querySelector(sel) as HTMLCanvasElement | null;
      if (!c) return false;
      try {
        return c.toDataURL() !== prevData;
      } catch {
        return false;
      }
    },
    { sel: canvasSelector, prevData: prev },
    { timeout }
  );
}

test.describe('Simulation Page', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/simulation');
  });

  test('AT-1.1: should render map on simulation page launch', async ({
    authenticatedPage,
  }) => {
    const canvas = authenticatedPage.locator('canvas').first();
    await expect(canvas).toBeVisible({ timeout: 15000 });

    const canvasBox = await canvas.boundingBox();
    expect(canvasBox).not.toBeNull();
    expect(canvasBox!.width).toBeGreaterThan(800);
    expect(canvasBox!.height).toBeGreaterThan(400);

    await canvas.hover();
    // Add delay to ensure map is fully initialized
    await authenticatedPage.waitForTimeout(1000);

    // zoom in
    await authenticatedPage.mouse.wheel(0, -1000);
    await authenticatedPage.waitForTimeout(500); // Wait for zoom animation
    await waitForCanvasChange(authenticatedPage, 'canvas', 5000);

    // zoom out
    await authenticatedPage.mouse.wheel(0, 500);
    await authenticatedPage.waitForTimeout(500); // Wait for zoom animation
    await waitForCanvasChange(authenticatedPage, 'canvas', 5000);

    // panning the map
    const centerX = canvasBox!.x + canvasBox!.width / 2;
    const centerY = canvasBox!.y + canvasBox!.height / 2;

    await authenticatedPage.mouse.move(centerX, centerY);
    await authenticatedPage.waitForTimeout(100);
    await authenticatedPage.mouse.down();
    await authenticatedPage.waitForTimeout(100);
    await authenticatedPage.mouse.move(centerX + 100, centerY + 100, {
      steps: 10,
    });
    await authenticatedPage.waitForTimeout(100);
    await authenticatedPage.mouse.up();
    await authenticatedPage.waitForTimeout(300); // Wait for pan to complete
    await waitForCanvasChange(authenticatedPage, 'canvas', 5000);

    await authenticatedPage.mouse.down();
    await authenticatedPage.waitForTimeout(100);
    await authenticatedPage.mouse.move(centerX - 200, centerY - 200, {
      steps: 10,
    });
    await authenticatedPage.waitForTimeout(100);
    await authenticatedPage.mouse.up();
    await authenticatedPage.waitForTimeout(300); // Wait for pan to complete
    await waitForCanvasChange(authenticatedPage, 'canvas', 5000);

    await expect(canvas).toBeVisible();
  });

  test('AT-1.2: should render bike station icons', async ({
    authenticatedPage,
  }) => {
    const canvas = authenticatedPage.locator('canvas').first();
    await expect(canvas).toBeVisible({ timeout: 10000 });

    const stationImageResponse = authenticatedPage.waitForResponse(
      (r) => r.url().endsWith('/station.png') && r.status() === 200
    );

    await stationImageResponse;

    await waitForCanvasChange(authenticatedPage);
    await expect(canvas).toBeVisible();
  });

  test('AT-1.3: map fails to render', async ({ authenticatedPage }) => {
    // block map
    await authenticatedPage.route('**/tiles/**', (route) =>
      route.abort('failed')
    );
    await authenticatedPage.route('**/*.pbf', (route) => route.abort('failed'));
    await authenticatedPage.route('**/v4/**', (route) => route.abort('failed'));
    await authenticatedPage.route('**/styles/**', (route) =>
      route.abort('failed')
    );

    await authenticatedPage.goto('/simulation');

    const dialog = authenticatedPage.locator('[data-testid="error-dialog"]');
    await expect(dialog).toBeVisible({ timeout: 10000 });
    await expect(dialog).toContainText('Failed to load map');
    const retryButton = authenticatedPage.locator(
      '[data-testid="error-dialog-retry"]'
    );
    await expect(retryButton).toBeVisible();

    // unblock map
    await authenticatedPage.unroute('**/tiles/**');
    await authenticatedPage.unroute('**/*.pbf');
    await authenticatedPage.unroute('**/v4/**');
    await authenticatedPage.unroute('**/styles/**');

    // click retry
    await retryButton.click();

    const canvas = authenticatedPage.locator('canvas').first();
    await expect(canvas).toBeVisible({ timeout: 10000 });
  });

  test('AT-1.4: map renders but station markers fail to load', async ({
    authenticatedPage,
  }) => {
    // block station endpoint
    await authenticatedPage.route('**/stations**', (route) =>
      route.abort('failed')
    );

    await authenticatedPage.goto('/simulation');

    const canvas = authenticatedPage.locator('canvas').first();
    await expect(canvas).toBeVisible({ timeout: 10000 });

    const canvasBox = await canvas.boundingBox();
    expect(canvasBox).not.toBeNull();
    expect(canvasBox!.width).toBeGreaterThan(800);
    expect(canvasBox!.height).toBeGreaterThan(400);

    const dataUnavailableMessage = authenticatedPage.locator(
      '[data-testid="error-dialog"]'
    );
    await expect(dataUnavailableMessage).toBeVisible({ timeout: 5000 });
    await expect(dataUnavailableMessage).toContainText('Station load error');

    // click on close button
    const closeButton = dataUnavailableMessage.locator(
      '[data-testid="error-dialog-close"]'
    );

    await expect(closeButton).toBeVisible();
    await closeButton.click();

    await expect(dataUnavailableMessage).toBeHidden({ timeout: 3000 });

    // ensure map remains interactive - zoom in and out
    await canvas.hover();
    await authenticatedPage.mouse.wheel(0, -500);
    await waitForCanvasChange(authenticatedPage);

    await authenticatedPage.mouse.wheel(0, 300);
    await waitForCanvasChange(authenticatedPage);

    // ensure map remains interactive - panning
    const centerX = canvasBox!.x + canvasBox!.width / 2;
    const centerY = canvasBox!.y + canvasBox!.height / 2;

    await authenticatedPage.mouse.move(centerX, centerY);
    await authenticatedPage.mouse.down();
    await authenticatedPage.mouse.move(centerX + 100, centerY + 100);
    await authenticatedPage.mouse.up();
    await waitForCanvasChange(authenticatedPage);

    await expect(canvas).toBeVisible();
  });
});
