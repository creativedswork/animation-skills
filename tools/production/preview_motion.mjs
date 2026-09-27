// Inspect an exported file using the viewer's public file and timeline controls.
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
const [playwrightPath, id, revision = 'initial', camera = 'perspective', ...times] = process.argv.slice(2);
const { chromium } = await import(pathToFileURL(playwrightPath).href);
const out = path.resolve('.artifacts/production', id, revision);
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1080 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
await page.goto(`http://127.0.0.1:8765/#${id}`);
await page.locator('#viewport-a[data-state="ready"]').waitFor();
await page.locator('#viewport-a .file-input').setInputFiles(path.join(out, 'animation.glb'));
await page.locator('#viewport-a[data-state="ready"][data-kind="local"]').waitFor();
await page.locator(`[data-camera="${camera}"]`).click();
const duration = Number(await page.locator('#timeline').getAttribute('max'));
for (const value of times.length ? times : ['0', String(duration / 2), String(duration)]) {
  const timeline = page.locator('#timeline');
  const rect = await timeline.boundingBox();
  await timeline.click({ position: { x: 8 + (rect.width - 16) * Number(value) / duration, y: rect.height / 2 } });
  await page.locator('#viewport-a canvas').screenshot({ path: path.join(out, `${camera}-${value}.png`) });
}
const result = { id, revision, camera, duration, errors,
  clip: await page.locator('#viewport-a .clip-select option:checked').textContent() };
fs.writeFileSync(path.join(out, `preview-${camera}.json`), JSON.stringify(result, null, 2));
console.log(result);
await browser.close();
