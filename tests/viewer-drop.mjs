// Browser regression with a supplied animated GLB. See docs/viewer-testing.md.
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, basename, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const [playwrightEntry, modelPath, url = 'http://127.0.0.1:8765'] = process.argv.slice(2);
assert(playwrightEntry && modelPath, 'Usage: node tests/viewer-drop.mjs <playwright-entry> <animated.glb> [url]');
const { chromium } = await import(pathToFileURL(resolve(playwrightEntry)).href);
const model = resolve(modelPath);
const temporary = await mkdtemp(join(tmpdir(), 'animation-viewer-'));
const invalid = join(temporary, 'invalid.txt'), corrupt = join(temporary, 'corrupt.glb');
await writeFile(invalid, 'Not a GLB');
await writeFile(corrupt, 'Not a GLB');
const browser = await chromium.launch({ channel: 'chrome', headless: true });

try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.method() !== 'GET') writes.push(request.url()); });
  await page.goto(url + '/#sit-stand');
  await page.locator('#viewport-a[data-state="ready"], #viewport-a[data-state="error"]').waitFor();
  const cdp = await page.context().newCDPSession(page);
  const point = async selector => {
    const box = await page.locator(selector).boundingBox();
    assert(box, `${selector} must be visible`);
    return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  };
  // Chromium creates the File objects from disk, as for a native file drag.
  const drag = async (type, selector, files) => cdp.send('Input.dispatchDragEvent', {
    type, ...await point(selector), data: { items: [], files, dragOperationsMask: 1 },
  });
  const drop = async (selector, files) => {
    await drag('dragEnter', selector, files);
    await drag('dragOver', selector, files);
    await drag('drop', selector, files);
  };
  const ready = pane => page.locator(`#viewport-${pane}[data-state="ready"][data-kind="local"]`).waitFor();
  const errorText = async () => {
    await page.locator('#viewport-a[data-state="error"]').waitFor();
    return page.locator('#viewport-a .canvas-status').textContent();
  };

  // CDP dragCancel emits no target dragleave; move out before ending the drag.
  await drag('dragEnter', '#viewport-a canvas', [model]);
  await drag('dragOver', '#viewport-a canvas', [model]);
  assert(await page.locator('#viewport-a .drop-hint').isVisible());
  await drag('dragOver', '#viewport-a .viewport-toolbar', [model]);
  assert(await page.locator('#viewport-a .drop-hint').isVisible());
  await drag('dragOver', '.app-header', [model]);
  await page.locator('#viewport-a .drop-hint').waitFor({ state: 'hidden' });
  await drag('dragCancel', '.app-header', [model]);

  await drop('#viewport-a canvas', [model]);
  await ready('a');
  assert.equal(await page.locator('#viewport-a .model-select option:checked').textContent(), basename(model));
  assert.equal(await page.locator('#viewport-a .clip-select').inputValue(), '0');
  const duration = Number(await page.locator('#timeline').getAttribute('max'));
  assert(duration > 0, 'Supply a GLB with animation');
  await page.locator('[data-camera="side"]').click();
  const before = await page.locator('#viewport-a canvas').screenshot();
  await page.locator('#loop').uncheck();
  await page.locator('#play').click();
  await page.waitForFunction(t => Number(document.querySelector('#timeline').value) >= t,
    Math.min(1.8, duration * 0.4), { timeout: 10000 });
  await page.locator('#play').click();
  const after = await page.locator('#viewport-a canvas').screenshot();
  assert(!before.equals(after), 'The rendered pose must change during playback');

  await page.locator('#compare').click();
  await drop('#viewport-b canvas', [model]);
  await ready('b');
  await page.locator('#viewport-b .clip-select').selectOption('');
  assert.equal(await page.locator('#viewport-a .clip-select').inputValue(), '0');
  await page.locator('#viewport-b .file-input').setInputFiles(model);
  await ready('b');
  assert.equal(await page.locator('#viewport-b .clip-select').inputValue(), '0');
  assert.equal(await page.locator('#viewport-b .model-select option[value="local"]').count(), 1);

  await drop('#viewport-a canvas', [invalid]);
  assert.match(await errorText(), /仅支持 GLB/);
  await drop('#viewport-a canvas', [corrupt]);
  assert.match(await errorText(), /GLB 无法读取/);
  await drop('#viewport-a canvas', [model, corrupt]);
  assert.match(await errorText(), /一次载入一个/);
  await ready('b');
  await drop('#viewport-a canvas', [model]);
  await ready('a');

  const location = page.url();
  await drop('.app-header', [model]);
  assert.equal(page.url(), location, 'Dropping outside must not navigate away');
  await ready('a');
  assert.equal(await page.locator('.drag-over').count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(writes, [], 'Loading local files must not upload them');
  await mkdir('.artifacts/viewer-drop', { recursive: true });
  await page.screenshot({ path: '.artifacts/viewer-drop/viewer.png' });
  const result = { browser: browser.version(), url, file: basename(model), duration,
    passed: ['drag hint', 'nested drag', 'cancel', 'drop A', 'animation playback', 'drop B',
      'independent clips', 'file picker', 'invalid extension', 'corrupt GLB', 'multiple files',
      'recovery', 'outside drop', 'no upload', 'no uncaught errors'] };
  await writeFile('.artifacts/viewer-drop/result.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser.close();
  await rm(temporary, { recursive: true, force: true });
}
