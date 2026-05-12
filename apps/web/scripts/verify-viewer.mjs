import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

const baseUrl = process.env.DREAMNAV_VERIFY_URL ?? "http://localhost:3001";
const outputDir = join(process.cwd(), "../../.context/viewer-checks");
const startupTimeoutMs = 30000;

const viewports = [
  { name: "desktop", width: 1440, height: 960 },
  { name: "mobile", width: 390, height: 844 }
];

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch();

try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    const pageErrors = [];
    const splatResponseStatuses = [];

    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("response", (response) => {
      if (response.url().endsWith("/splat.ply")) {
        splatResponseStatuses.push(response.status());
      }
    });

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await waitForStartupState(page);
    const openDemoButton = page.getByRole("button", { name: "Open demo" });

    if (await openDemoButton.isVisible()) {
      await openDemoButton.click();
    }

    await page.locator("[data-testid='scene-canvas']").waitFor();
    const renderMode = await page.locator("[aria-label='Render mode']").textContent();

    if (!renderMode?.includes("3DGS")) {
      throw new Error(`Expected 3DGS render mode in ${viewport.name} viewport`);
    }

    await page.waitForTimeout(2000);

    if (pageErrors.length > 0) {
      throw new Error(`Browser error in ${viewport.name} viewport: ${pageErrors.join("; ")}`);
    }

    if (!splatResponseStatuses.some((status) => status >= 200 && status < 300)) {
      throw new Error(`Splat asset did not load in ${viewport.name} viewport`);
    }

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

async function waitForStartupState(page) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < startupTimeoutMs) {
    if (await page.locator("[data-testid='scene-canvas']").count()) {
      return;
    }

    if (await page.getByRole("button", { name: "Open demo" }).count()) {
      return;
    }

    if (await page.getByText("Scene API unavailable", { exact: true }).count()) {
      throw new Error("Home page reached the API unavailable state before the explorer could load.");
    }

    await page.waitForTimeout(250);
  }

  throw new Error("Home page never reached a usable startup state.");
}
