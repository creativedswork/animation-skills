// Offline video rendering: sample the public timeline at the case FPS, without wall-clock playback.
import { pathToFileURL } from 'node:url';
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawn, execFileSync } from 'node:child_process';
import { once } from 'node:events';
import { createHash } from 'node:crypto';
const { chromium } = await import(pathToFileURL(process.argv[2]).href);
const [caseId, version = 'initial', only] = process.argv.slice(3);
const out = `.artifacts/production/${caseId}/${version}`;
const task = JSON.parse(await readFile(`cases/${caseId}/case.json`, 'utf8'));
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 2234, height: 1600 } });
  await page.goto(`http://127.0.0.1:8765/#${caseId}`);
  await page.locator('#viewport-a[data-state="ready"]').waitFor();
  await page.locator('#viewport-a .file-input').setInputFiles(`${out}/animation.glb`);
  await page.locator('#viewport-a[data-state="ready"][data-kind="local"]').waitFor();
  await page.addStyleTag({ content: 'main{max-width:none} #viewport-a .canvas-wrap{width:1920px;height:1080px}' });
  for (const filename of task.deliverables.filter(name => name.endsWith('.mp4'))) {
    const name = filename.slice(0, -4);
    if (only && only !== name) continue;
    const target = `${out}/${name}-offline.mp4`;
    if (existsSync(target)) continue;
    await page.locator(`[data-camera="${name === 'main' ? 'perspective' : name}"]`).click();
    const encoder = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate',
      String(task.fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-threads', '2',
      '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', target],
      { stdio: ['pipe', 'ignore', 'inherit'] });
    const exit = once(encoder, 'close');
    const count = task.duration_seconds * task.fps;
    const poses = new Set();
    for (let frame = 0; frame < count; frame++) {
      const png = await page.evaluate(seconds => {
        const slider = document.querySelector('#timeline');
        slider.value = String(seconds);
        slider.dispatchEvent(new Event('input', { bubbles: true }));
        return new Promise(resolve => requestAnimationFrame(() => {
          resolve(document.querySelector('#viewport-a canvas').toDataURL('image/png').split(',')[1]);
        }));
      }, frame / task.fps);
      const bytes = Buffer.from(png, 'base64');
      poses.add(createHash('sha256').update(bytes).digest('hex'));
      if (!encoder.stdin.write(bytes)) await once(encoder.stdin, 'drain');
    }
    encoder.stdin.end();
    const [code] = await exit;
    if (code) throw new Error(`ffmpeg exited ${code}`);
    const media = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries',
      'stream=width,height,nb_frames,r_frame_rate:format=duration', '-of', 'json', target]));
    if (Number(media.streams[0].nb_frames) !== count) throw new Error('Missing rendered frames');
    if (poses.size < 2) throw new Error('Rendered images did not change');
    const evidence = { case: caseId, version, camera: name, method: 'Offline sampling through public timeline input',
      fps: task.fps, frames: count, distinct_images: poses.size,
      seconds: task.duration_seconds, browser: browser.version(), media,
      note: 'Every pose sampled at frame/fps and rendered, then encoded at the same fps. Not a realtime recording.' };
    await writeFile(`${out}/${name}-rendering.json`, JSON.stringify(evidence, null, 2));
    console.log(JSON.stringify(evidence));
  }
} finally {
  await browser.close();
}
