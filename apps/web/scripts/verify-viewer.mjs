import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

const baseUrl = process.env.DREAMNAV_VERIFY_URL ?? "http://127.0.0.1:3000";
const outputDir = join(process.cwd(), "../../.context/viewer-checks");

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "mobile", width: 390, height: 844 }
];

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch();

try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.locator("[data-testid='scene-canvas']").waitFor();
    await page.screenshot({ path: join(outputDir, `${viewport.name}.png`), fullPage: true });

    const pixelStats = await page.locator("[data-testid='scene-canvas']").evaluate((canvas) => {
      const typedCanvas = canvas;
      const context = typedCanvas.getContext("webgl2") ?? typedCanvas.getContext("webgl");

      if (!context) {
        return { nonBlackPixels: 0 };
      }

      const width = typedCanvas.width;
      const height = typedCanvas.height;
      const pixels = new Uint8Array(width * height * 4);
      context.readPixels(0, 0, width, height, context.RGBA, context.UNSIGNED_BYTE, pixels);

      let nonBlackPixels = 0;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] + pixels[index + 1] + pixels[index + 2] > 12) {
          nonBlackPixels += 1;
        }
      }

      return { nonBlackPixels };
    });

    if (pixelStats.nonBlackPixels < 100) {
      throw new Error(`Canvas appears blank in ${viewport.name} viewport`);
    }

    await page.close();
  }
} finally {
  await browser.close();
}
