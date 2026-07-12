# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.ts >> Mission Control Dashboard >> displays activity stream
- Location: tests\e2e\dashboard.spec.ts:22:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Activity Stream').first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Activity Stream').first()

```

```yaml
- navigation:
  - text: Agentic OS
  - link "Mission Control":
    - /url: /
  - link "Kanban":
    - /url: /kanban
  - link "Tokens":
    - /url: /tokens
  - link "HITL":
    - /url: /hitl
  - link "Crash":
    - /url: /crash
  - link "Agents":
    - /url: /agents
  - link "Vault":
    - /url: /vault
- heading "Backend Error" [level=2]
- paragraph: fetch failed
- button "Try again"
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('Mission Control Dashboard', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.route('**/health', route => route.fulfill({ json: { status: 'ok', obsidian_backend: true } }));
  6  |     await page.route('**/dashboard/state', route => route.fulfill({ json: { locks: [], recent_activity: [], agents: [], tasks: [], stalls: [] } }));
  7  |   });
  8  | 
  9  |   test('redirects to login when unauthenticated', async ({ page }) => {
  10 |     await page.goto('/');
  11 |     await expect(page).toHaveURL(/.*\/login/);
  12 |   });
  13 | 
  14 |   test('can login with correct token', async ({ page }) => {
  15 |     await page.goto('/login');
  16 |     await page.fill('input[type="password"]', 'admin-token-123');
  17 |     await page.click('button:has-text("Authenticate")');
  18 |     await expect(page).toHaveURL('/');
  19 |     await expect(page.locator('h1')).toContainText('Mission Control');
  20 |   });
  21 | 
  22 |   test('displays activity stream', async ({ page, context }) => {
  23 |     await context.addCookies([{ name: 'mission_control_token', value: 'admin-token-123', url: 'http://localhost:3000' }]);
  24 |     await page.goto('/');
  25 |     
  26 |     // The table header should be visible
> 27 |     await expect(page.locator('text=Activity Stream').first()).toBeVisible();
     |                                                                ^ Error: expect(locator).toBeVisible() failed
  28 |     await expect(page.locator('table th:has-text("Agent")')).toBeVisible();
  29 |   });
  30 | });
  31 | 
```