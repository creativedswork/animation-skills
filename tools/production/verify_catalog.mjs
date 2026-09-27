// Verify default registered clips through the viewer's visible case/play controls.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { writeFile } from 'node:fs/promises';
const { chromium } = await import(pathToFileURL(process.argv[2]).href);
const base = 'http://127.0.0.1:8765';
const { cases } = await (await fetch(`${base}/api/cases`)).json();
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const results = [], errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1080 } });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.locator('#viewport-a[data-state="ready"]').waitFor();
  for (const task of cases) {
    await page.locator(`[data-case="${task.id}"]`).click();
    await page.locator('#viewport-a[data-state="ready"]').waitFor();
    const modelId = await page.locator('#viewport-a .model-select').inputValue();
    const model = task.models.find(item => item.id === modelId);
    assert(model?.available && ['initial', 'corrected'].includes(model.kind), task.id);
    const seconds = Number(await page.locator('#timeline').getAttribute('max'));
    assert(Math.abs(seconds - task.duration_seconds) < .001, `${task.id}: ${seconds}`);
    const clip = await page.locator('#viewport-a .clip-select option:checked').textContent();
    assert(!['Idle', 'Walk', 'Chop', '绑定姿势'].includes(clip), `${task.id}: ${clip}`);
    await page.locator('#play').click();
    await page.waitForFunction(() => Number(document.querySelector('#timeline').value) > .25,
      null, { timeout: 10000 });
    await page.locator('#play').click();
    results.push({ case: task.id, kind: model.kind, model: modelId, clip, seconds, playback_advanced: true });
  }
  assert.equal(errors.length, 0);
  await writeFile('.artifacts/production/catalog-check.json',
    JSON.stringify({ browser: browser.version(), results, errors }, null, 2));
  console.log(JSON.stringify(results, null, 2));
} finally {
  await browser.close();
}
