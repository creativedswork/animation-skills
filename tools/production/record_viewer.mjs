// Capture the actual Three.js canvas at 1× speed through the public play controls.
import { pathToFileURL } from 'node:url';
import { writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const { chromium } = await import(pathToFileURL(process.argv[2]).href);
const caseId = process.argv[3], version = process.argv[4] || 'initial';
const out = `.artifacts/production/${caseId}/${version}`;
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width: 2234, height: 1600 } });
  await page.goto(`http://127.0.0.1:8765/#${caseId}`);
  await page.locator('#viewport-a[data-state="ready"]').waitFor();
  await page.locator('#viewport-a input[type="file"]').setInputFiles(`${out}/animation.glb`);
  await page.locator('#viewport-a[data-state="ready"][data-kind="local"]').waitFor();
  // Evidence-only viewport sizing; animation, camera positions and clocks are unchanged.
  await page.addStyleTag({ content: 'main{max-width:none} #viewport-a .canvas-wrap{width:1920px;height:1080px}' });
  await page.locator('#loop').uncheck();
  await page.locator('#speed').selectOption('1');
  for (const [camera, filename] of [['perspective', 'main'], ['side', 'side']]) {
    await page.locator(`[data-camera="${camera}"]`).click();
    await page.locator('#timeline').focus();
    await page.keyboard.press('Home');
    await page.evaluate(() => {
      const canvas = document.querySelector('#viewport-a canvas');
      window.captureChunks = [];
      window.capture = new MediaRecorder(canvas.captureStream(30), {
        mimeType: 'video/webm;codecs=vp9', videoBitsPerSecond: 8000000,
      });
      window.capture.ondataavailable = e => window.captureChunks.push(e.data);
      window.captureBytes = new Promise(resolve => {
        window.capture.onstop = async () => {
          const blob = new Blob(window.captureChunks, { type: 'video/webm' });
          resolve(Array.from(new Uint8Array(await blob.arrayBuffer())));
        };
      });
      const play = document.querySelector('#play');
      const observer = new MutationObserver(() => {
        if (play.getAttribute('aria-label') === '暂停' && window.capture.state === 'inactive') {
          window.capture.start();
        } else if (play.getAttribute('aria-label') === '播放' && window.capture.state === 'recording') {
          window.capture.stop();
          observer.disconnect();
        }
      });
      observer.observe(play, { attributes: true, attributeFilter: ['aria-label'] });
    });
    await page.locator('#play').click();
    await page.waitForFunction(() => document.querySelector('#play').getAttribute('aria-label') === '播放',
      null, { timeout: 20000 });
    const bytes = await page.evaluate(() => window.captureBytes);
    await writeFile(`${out}/${filename}.webm`, Buffer.from(bytes));
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', `${out}/${filename}.webm`,
      '-an', '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart', `${out}/${filename}.mp4`]);
    console.log(JSON.stringify({ case: caseId, version, camera, video: `${out}/${filename}.mp4` }));
  }
} finally {
  await browser.close();
}
