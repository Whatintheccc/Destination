// Optional Playwright/Test spec for teams using the Node runner.
// The repository's canonical CI-friendly smoke is scripts/run_browser_e2e.py,
// which starts the Python fixture server and drives the live frontend/API flow.
import { test, expect } from '@playwright/test';

test('interactive frontend dogfood flow', async ({ page }) => {
  await page.goto(process.env.CALENDAR_PILOT_URL || 'http://127.0.0.1:8787');
  await expect(page.getByTestId('chat-transcript')).toBeVisible();
  await page.getByTestId('goal-input').fill('Make next week less chaotic');
  await page.getByTestId('send-goal').click();
  await expect(page.getByTestId('candidate-card').first()).toBeVisible();
  await page.getByTestId('stage-candidate').first().click();
  await expect(page.getByTestId('receipt-card').first()).toBeVisible();
  await page.getByTestId('commit-candidate').first().click();
  await expect(page.getByTestId('undo-action').first()).toBeVisible();
  await page.getByTestId('undo-action').first().click();
  await expect(page.getByText('Undo requested')).toBeVisible();
  await page.getByTestId('feedback-useful').first().click();
  await expect(page.getByText('Feedback captured')).toBeVisible();
  await page.getByTestId('inspector-toggle').click();
  await page.locator('#tab-replay').click();
  await page.getByTestId('replay-export').click();
  await expect(page.locator('#replay-json')).toContainText('records');
});
