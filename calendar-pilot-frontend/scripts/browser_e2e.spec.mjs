import { test, expect } from '@playwright/test';

const baseURL = process.env.CALENDAR_PILOT_BASE_URL;
if (!baseURL) {
  throw new Error('CALENDAR_PILOT_BASE_URL is required');
}

test('goal to stage confirm commit undo feedback training loop', async ({ page }) => {
  await page.goto(baseURL, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Reset fixture state' }).click();
  await page.getByRole('textbox').first().fill('Make next week less chaotic');
  const commitBox = page.locator('#commit-now');
  if (await commitBox.isChecked()) {
    await commitBox.uncheck();
  }
  await page.getByRole('button', { name: 'Create plan' }).click();
  await page.getByRole('button', { name: 'Stage' }).first().waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Stage' }).first().click();
  await page.getByRole('button', { name: 'Confirm' }).first().waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Confirm' }).first().click();
  await page.locator('.status.committed').first().waitFor({ timeout: 15000 });
  await page.getByRole('button', { name: 'Undo', exact: true }).first().click();
  await page.getByRole('heading', { name: 'Undo journey' }).waitFor({ timeout: 15000 });
  await page.getByText('reverted').first().waitFor({ timeout: 15000 });
  const committedAction = page.locator('.action').filter({ has: page.getByRole('button', { name: 'Undo', exact: true }) }).first();
  await committedAction.getByRole('button', { name: 'Accepted', exact: true }).click();
  await page.waitForFunction(() => {
    return Array.from(document.querySelectorAll('.summary div')).some((node) => {
      const text = node.textContent || '';
      return text.includes('training rows') && /[1-9]/.test(text);
    });
  }, { timeout: 15000 });
  await expect(page.locator('#undo-history')).toContainText('reverted');
  await expect(page.locator('#feedback-history')).toContainText('rew_');

  await page.locator('#profile-correction').fill('evenings are fine during travel weeks');
  await page.getByRole('button', { name: 'Propose patch' }).click();
  await page.locator('#profile-patch').getByRole('button', { name: 'Apply' }).first().waitFor({ timeout: 15000 });
  await page.locator('#profile-patch').getByRole('button', { name: 'Apply' }).first().click();
  await expect(page.locator('#profile-patch')).toContainText('evenings are fine', { timeout: 15000 });

  await page.locator('#authority-scopes').fill('recommend,stage,undo');
  await page.locator('#authority-editor-tier').fill('2');
  await page.getByRole('button', { name: 'Set authority' }).click();
  await expect(page.locator('#authority-scopes')).toHaveValue('recommend,stage,undo', { timeout: 15000 });

  await page.locator('#replay-query').fill('rew_');
  await page.getByRole('button', { name: 'Query replay' }).click();
  await expect(page.locator('#replay-explorer')).toContainText('reward', { timeout: 15000 });
  await page.getByRole('button', { name: 'Export JSONL' }).click();
  await expect(page.locator('#replay-explorer')).toContainText('replay_export', { timeout: 15000 });

  await page.locator('#self-play-episodes').fill('1');
  await page.getByRole('button', { name: 'Run self-play' }).click();
  await expect(page.locator('#self-play-history')).toContainText(/hold_autonomy|ship_fixture_gate/, { timeout: 15000 });
});
