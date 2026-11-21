// 대본 JSON으로 인스타 캐러셀 이미지(1080x1350, 4:5) 만들기
// 사용: node carousel.js scripts/006_ai_daily_20261121.json [output]
//   -> output/<id>_carousel/01.png, 02.png, ...
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const [, , scriptPath, outRoot = "output"] = process.argv;
  const s = JSON.parse(fs.readFileSync(scriptPath, "utf8"));
  const outDir = path.join(outRoot, `${s.id}_carousel`);
  fs.mkdirSync(outDir, { recursive: true });
  for (const f of fs.readdirSync(outDir)) if (f.endsWith(".png")) fs.unlinkSync(path.join(outDir, f));
  const browser = await chromium.launch({ args: ["--allow-file-access-from-files"] });
  const page = await browser.newPage({ viewport: { width: 1100, height: 1400 }, deviceScaleFactor: 1 });
  page.on("pageerror", e => { console.error("page error:", e.message); process.exitCode = 1; });
  await page.goto("file://" + path.resolve(__dirname, "templates", "carousel.html"));
  const n = await page.evaluate(d => window.build(d), s);
  for (let i = 1; i <= n; i++) {
    await page.locator("#s" + i).screenshot({ path: path.join(outDir, String(i).padStart(2, "0") + ".png") });
  }
  await browser.close();
  console.log(`캐러셀 ${n}장: ${outDir}`);
})().catch(e => { console.error(e); process.exit(1); });
