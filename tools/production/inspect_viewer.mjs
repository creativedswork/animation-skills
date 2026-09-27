// Run from the repository root; argv[2] is an installed Playwright entry point.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
const { chromium } = await import(pathToFileURL(process.argv[2]).href);
const caseId = process.argv[3];
const version = process.argv[4] || 'initial';
const out = `.artifacts/production/${caseId}/${version}`;
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(`http://127.0.0.1:8765/#${caseId}`);
  await page.locator('#viewport-a[data-state="ready"]').waitFor();
  if (process.env.REGISTERED !== '1') {
    await page.locator('#viewport-a input[type="file"]').setInputFiles(`${out}/animation.glb`);
    await page.locator('#viewport-a[data-state="ready"][data-kind="local"]').waitFor();
  } else {
    assert.equal(await page.locator('#viewport-a').getAttribute('data-kind'), version);
  }
  await page.locator('#loop').uncheck();
  const duration = Number(await page.locator('#timeline').getAttribute('max'));
  const expectedDuration = caseId === 'sit-stand' ? 7 : 6;
  const durationError = duration - expectedDuration;
  const clip = await page.locator('#viewport-a .clip-select option:checked').textContent();
  assert(!['Idle', 'Walk', 'Chop'].includes(clip));
  await mkdir(`${out}/views`, { recursive: true });
  const times = caseId === 'sit-stand' ? [0, 1.3, 2.7, 4.2, 5.2, 7] : [0, 1.3, 2.7, 3.75, 4.2, 6];
  for (const camera of (process.env.REGISTERED === '1' ? [] : ['perspective', 'side'])) {
    await page.locator(`[data-camera="${camera}"]`).click();
    for (const t of times) {
      const bounds = await page.locator('#timeline').boundingBox();
      await page.mouse.click(bounds.x + 8 + (bounds.width - 16) * t / duration, bounds.y + bounds.height / 2);
      await page.locator('#viewport-a canvas').screenshot({ path: `${out}/views/${camera}-${t}.png` });
    }
  }
  await page.locator('[data-camera="perspective"]').click();
  await page.locator('#timeline').focus();
  await page.keyboard.press('Home');
  const before = await page.locator('#viewport-a canvas').screenshot();
  await page.locator('#play').click();
  await page.waitForFunction(() => Number(document.querySelector('#timeline').value) > 1.8);
  await page.locator('#play').click();
  const after = await page.locator('#viewport-a canvas').screenshot();
  assert(!before.equals(after));
  await page.screenshot({ path: `${out}/views/viewer.png` });
  assert.deepEqual(errors, []);
  const result = { case: caseId, version, clip, duration, durationError, errors, observedPlayback: true,
    renderedPoseChanged: true, registered: process.env.REGISTERED === '1' };
  await writeFile(`${out}/viewer-check.json`, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  assert(Math.abs(durationError) < .001, 'Exported duration must match the task');
} finally {
  await browser.close();
}
