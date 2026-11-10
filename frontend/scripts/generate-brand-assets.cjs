// Renders the Nomica seal mark to every icon the app and LINE use. Run from frontend/:
//   node scripts/generate-brand-assets.cjs
// Needs Playwright with a local Chrome (the same one the UI tests use).
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const publicDir = path.join(__dirname, '..', 'public');
const TEAL = '#23656D';
const LIGHT_TEAL = '#9FE0DA';

/** The mark on a 1024 canvas. `inset` shrinks the artwork for maskable icons; `frame` is the seal border width. */
function markSvg({ inset = 0, frame = 22, round = false } = {}) {
  const scale = 1 - inset * 2 / 1024;
  return `<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
  <rect width="1024" height="1024" fill="${TEAL}"/>
  <g transform="translate(512 512) scale(${scale}) translate(-512 -512)">
    ${round
      // LINE shows profile images as circles, so the seal border becomes a ring that is never cropped.
      ? `<circle cx="512" cy="512" r="420" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="${frame}"/>`
      : `<rect x="92" y="92" width="840" height="840" rx="60" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="${frame}"/>`}
    <g transform="translate(0 32)">
      <path d="M300 260L724 700" fill="none" stroke="${LIGHT_TEAL}" stroke-width="86" stroke-linecap="round"/>
      <path d="M300 700V260M724 700V260" fill="none" stroke="#fff" stroke-width="96" stroke-linecap="round"/>
    </g>
  </g></svg>`;
}

const targets = [
  { file: 'app-icon-512.png', size: 512 },
  { file: 'app-icon-192.png', size: 192 },
  { file: 'app-icon-maskable-512.png', size: 512, inset: 150 },
  { file: 'apple-touch-icon.png', size: 180 },
  { file: 'favicon.png', size: 32, frame: 48 },
  { file: 'nomica-line-profile-640.png', size: 640, round: true },
  { file: 'line-logo.png', size: 4000, round: true },
];

(async () => {
  const browser = await chromium.launch({ ...(process.env.UI_BROWSER_CHANNEL ? { channel: process.env.UI_BROWSER_CHANNEL } : {}) });
  fs.writeFileSync(path.join(publicDir, 'nomica-mark.svg'), markSvg().replace('<svg ', '<svg role="img" aria-label="Nomica" ') + '\n');
  for (const { file, size, inset, frame, round } of targets) {
    const context = await browser.newContext({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    await page.setContent(`<style>*{margin:0}svg{display:block;width:${size}px;height:${size}px}</style>${markSvg({ inset, frame, round })}`);
    await page.screenshot({ path: path.join(publicDir, file), type: 'png' });
    await context.close();
  }
  await browser.close();
  // The ICO wraps the 32 px PNG so browsers that still ask for /favicon.ico get the same mark.
  const png = fs.readFileSync(path.join(publicDir, 'favicon.png'));
  const header = Buffer.from([0, 0, 1, 0, 1, 0, 32, 32, 0, 0, 1, 0, 32, 0]);
  const tail = Buffer.alloc(8);
  tail.writeUInt32LE(png.length, 0);
  tail.writeUInt32LE(22, 4);
  fs.writeFileSync(path.join(publicDir, 'favicon.ico'), Buffer.concat([header, tail, png]));
})();
