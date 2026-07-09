import { test, expect } from '@playwright/test';

test.describe('Mission Control Dashboard', () => {
  test('redirects to login when unauthenticated', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/.*\/login/);
  });

  test('can login with correct token', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="password"]', 'admin-token-123');
    await page.click('button:has-text("Authenticate")');
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('Mission Control');
  });

  test('displays activity stream', async ({ page, context }) => {
    await context.addCookies([{ name: 'mission_control_token', value: 'admin-token-123', url: 'http://localhost:3000' }]);
    await page.goto('/');
    
    // The table header should be visible
    await expect(page.locator('text=Activity Stream').first()).toBeVisible();
    await expect(page.locator('table th:has-text("Agent")')).toBeVisible();
  });
});
