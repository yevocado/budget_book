// HTML 템플릿을 브라우저에서 열고 프레임마다 seek(t) -> 스크린샷 -> ffmpeg로 영상(무음) 생성.
// 사용: node render.js <timeline.json> <out_video.mp4> <out_sfx.json> [--frames 0,1.5,3 --png-dir dir]
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const { chromium } = require("playwright");

const [, , dataPath, outVideo, outSfx, ...rest] = process.argv;
const opt = {};
for (let i = 0; i < rest.length; i += 2) opt[rest[i].replace(/^--/, "")] = rest[i + 1];
const FPS = 30;

(async () => {
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  const browser = await chromium.launch({ args: ["--disable-web-security", "--allow-file-access-from-files"] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on("pageerror", e => { console.error("page error:", e.message); process.exitCode = 1; });
  await page.goto("file://" + path.resolve(__dirname, "templates", "reel.html"));
  const sfx = await page.evaluate(d => window.build(d), data);
  fs.writeFileSync(outSfx, JSON.stringify(sfx));

  // 미리보기용: 특정 시점 PNG만 저장
  if (opt.frames) {
    fs.mkdirSync(opt["png-dir"], { recursive: true });
    for (const t of opt.frames.split(",").map(Number)) {
      await page.evaluate(t => window.seek(t), t);
      await page.screenshot({ path: path.join(opt["png-dir"], `t${t.toFixed(2)}.png`) });
    }
    await browser.close();
    return;
  }

  // 고화질: 프레임은 무손실 PNG, H.264 High 프로파일 CRF 16 (화질 우선, 파일은 커짐)
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
    "-c:v", "libx264", "-preset", "slow", "-crf", String(process.env.REEL_CRF || 16), "-profile:v", "high", "-level", "4.2",
    "-pix_fmt", "yuv420p", "-x264-params", "aq-mode=3", outVideo], { stdio: ["pipe", "inherit", "inherit"] });
  const n = Math.ceil(data.total * FPS);
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.seek(t), i / FPS);
    const buf = await page.screenshot({ type: "png" });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (i % 150 === 0) console.log(`  프레임 ${i}/${n} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on("close", c => (c === 0 ? res() : rej(new Error("ffmpeg " + c)))));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
