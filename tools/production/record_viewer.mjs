// Capture the actual Three.js canvas at 1× speed through the public play controls.
import { pathToFileURL } from 'node:url';
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
const { chromium } = await import(pathToFileURL(process.argv[2]).href);
const caseId = process.argv[3], version = process.argv[4] || 'initial';
const out = `.artifacts/production/${caseId}/${version}`;
const task = JSON.parse(await readFile(`cases/${caseId}/case.json`, 'utf8'));
const cameras = task.deliverables.filter(name => name.endsWith('.mp4')).map(name =>
  [name === 'main.mp4' ? 'perspective' : name.slice(0, -4), name.slice(0, -4)]);
const records = existsSync(`${out}/recording.json`)
  ? JSON.parse(await readFile(`${out}/recording.json`, 'utf8')) : [];
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
  // Compile the loaded mesh/shadow shaders before measuring the final take.
  await page.locator('#play').click();
  await page.waitForFunction(() => Number(document.querySelector('#timeline').value) > .3,
    null, { timeout: 10000 });
  await page.locator('#play').click();
  for (const [camera, filename] of cameras) {
    if (existsSync(`${out}/${filename}.mp4`)) continue;
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
        if (play.getAttribute('aria-label') === '暂停') {
          window.playbackStartedAt = performance.now();
        } else if (play.getAttribute('aria-label') === '播放' && window.capture.state === 'recording') {
          window.playbackStoppedAt = performance.now();
          window.capture.stop();
          observer.disconnect();
        }
      });
      observer.observe(play, { attributes: true, attributeFilter: ['aria-label'] });
      window.capture.start();
    });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
    const started = Date.now();
    await page.locator('#play').click();
    await page.waitForFunction(() => document.querySelector('#play').getAttribute('aria-label') === '播放',
      null, { timeout: 60000 });
    const bytes = await page.evaluate(() => window.captureBytes);
    await writeFile(`${out}/${filename}.webm`, Buffer.from(bytes));
    const playbackSeconds = await page.evaluate(() => (window.playbackStoppedAt - window.playbackStartedAt) / 1000);
    if (Math.abs(playbackSeconds - task.duration_seconds) > .3) {
      throw new Error(`Playback stalled: ${playbackSeconds} s for ${task.duration_seconds} s clip`);
    }
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', `${out}/${filename}.webm`,
      '-an', '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart', `${out}/${filename}-capture.mp4`]);
    const capturedSeconds = Number(JSON.parse(execFileSync('ffprobe', ['-v', 'error',
      '-show_entries', 'format=duration', '-of', 'json', `${out}/${filename}-capture.mp4`])).format.duration);
    if (capturedSeconds < task.duration_seconds - .1) throw new Error(`Incomplete capture: ${capturedSeconds} s`);
    const lead = Math.max(0, capturedSeconds - task.duration_seconds);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', String(lead),
      '-i', `${out}/${filename}-capture.mp4`, '-t', String(task.duration_seconds),
      '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart', `${out}/${filename}.mp4`]);
    const media = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries',
      'stream=width,height,nb_frames,r_frame_rate:format=duration', '-of', 'json', `${out}/${filename}.mp4`]));
    const record = { case: caseId, version, camera, video: `${out}/${filename}.mp4`,
      clip: await page.locator('#viewport-a .clip-select option:checked').textContent(),
      timeline: await page.locator('#time').textContent(), browser: browser.version(),
      capture_and_encode_seconds: (Date.now() - started) / 1000, playback_seconds: playbackSeconds,
      trimmed_paused_lead_seconds: lead, media,
      note: '1× public playback, 1920×1080. Paused capture lead removed; untrimmed capture retained; no speed change.' };
    const previous = records.findIndex(item => item.camera === camera);
    if (previous >= 0) records[previous] = record;
    else records.push(record);
    console.log(JSON.stringify(record));
  }
  if (records.length) await writeFile(`${out}/recording.json`, JSON.stringify(records, null, 2));
} finally {
  await browser.close();
}
