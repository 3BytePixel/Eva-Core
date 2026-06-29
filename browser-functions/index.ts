import { defineFn } from "@browserbasehq/sdk-functions";
import { chromium } from "playwright-core";

/**
 * Parameterized page scraper.
 *
 * Params:
 *   url       (string, required)  Page to load.
 *   selector  (string, optional)  CSS selector to wait for and extract text from.
 *                                 When given multiple matches, all text is returned.
 *   timeoutMs (number, optional)  Navigation/selector timeout (default 30000).
 *
 * Run locally:  pnpm bb dev index.ts
 * Publish:      pnpm bb publish index.ts
 */
type ScrapeParams = {
  url?: string;
  selector?: string;
  timeoutMs?: number;
};

defineFn("scrape-page", async (context) => {
  const session = context.session;
  const params = (context.params ?? {}) as ScrapeParams;

  const url = params.url;
  const selector = params.selector;
  const timeoutMs = Number(params.timeoutMs ?? 30000);

  if (!url) {
    return { success: false, error: "Missing required param 'url'." };
  }

  console.log("Connecting to browser session:", session.id);
  const browser = await chromium.connectOverCDP(session.connectUrl);
  const page = browser.contexts()[0]!.pages()[0]!;

  try {
    console.log(`Navigating to ${url} ...`);
    await page.goto(url, { timeout: timeoutMs, waitUntil: "domcontentloaded" });

    const title = await page.title();

    let items: string[] | null = null;
    if (selector) {
      await page.waitForSelector(selector, { timeout: timeoutMs });
      items = await page.$$eval(selector, (els) =>
        els.map((el) => el.textContent?.trim() ?? "").filter(Boolean),
      );
    }

    console.log(`Done. title="${title}"${items ? `, ${items.length} item(s)` : ""}`);
    return {
      success: true,
      url,
      title,
      selector: selector ?? null,
      count: items ? items.length : null,
      items,
      timestamp: new Date().toISOString(),
    };
  } catch (error) {
    return {
      success: false,
      url,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
});
