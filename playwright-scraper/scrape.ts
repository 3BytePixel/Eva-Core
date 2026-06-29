import { chromium } from "playwright";

/**
 * Local Playwright page scraper.
 *
 * Launches a local headless Chromium, loads a URL, and returns the page title
 * plus (optionally) text extracted for a CSS selector. Can also save a
 * screenshot.
 *
 * Usage:
 *   pnpm scrape <url> [--selector <css>] [--screenshot <path>] [--timeout <ms>] [--headed]
 *
 * Examples:
 *   pnpm scrape https://example.com --selector h1
 *   pnpm scrape https://news.ycombinator.com --selector ".titleline > a" --screenshot hn.png
 */

export type ScrapeOptions = {
  url: string;
  selector?: string;
  screenshot?: string;
  timeoutMs?: number;
  headed?: boolean;
};

export type ScrapeResult = {
  url: string;
  title: string;
  selector: string | null;
  count: number | null;
  items: string[] | null;
  screenshot: string | null;
  timestamp: string;
};

export async function scrape(options: ScrapeOptions): Promise<ScrapeResult> {
  const { url, selector, screenshot } = options;
  const timeoutMs = options.timeoutMs ?? 30000;

  const browser = await chromium.launch({ headless: !options.headed });
  try {
    const page = await browser.newPage();
    await page.goto(url, { timeout: timeoutMs, waitUntil: "domcontentloaded" });

    const title = await page.title();

    let items: string[] | null = null;
    if (selector) {
      await page.waitForSelector(selector, { timeout: timeoutMs });
      items = await page.$$eval(selector, (els) =>
        els.map((el) => el.textContent?.trim() ?? "").filter(Boolean),
      );
    }

    let screenshotPath: string | null = null;
    if (screenshot) {
      await page.screenshot({ path: screenshot, fullPage: true });
      screenshotPath = screenshot;
    }

    return {
      url,
      title,
      selector: selector ?? null,
      count: items ? items.length : null,
      items,
      screenshot: screenshotPath,
      timestamp: new Date().toISOString(),
    };
  } finally {
    await browser.close();
  }
}

function parseArgs(argv: string[]): ScrapeOptions {
  const [url, ...rest] = argv;
  if (!url) {
    console.error(
      "Usage: pnpm scrape <url> [--selector <css>] [--screenshot <path>] [--timeout <ms>] [--headed]",
    );
    process.exit(1);
  }
  const opts: ScrapeOptions = { url };
  for (let i = 0; i < rest.length; i++) {
    const arg = rest[i];
    if (arg === "--selector") opts.selector = rest[++i];
    else if (arg === "--screenshot") opts.screenshot = rest[++i];
    else if (arg === "--timeout") opts.timeoutMs = Number(rest[++i]);
    else if (arg === "--headed") opts.headed = true;
  }
  return opts;
}

// Run as CLI when invoked directly (not when imported by tests).
const invokedDirectly =
  process.argv[1] && import.meta.url === `file://${process.argv[1]}`;
if (invokedDirectly) {
  scrape(parseArgs(process.argv.slice(2)))
    .then((result) => {
      console.log(JSON.stringify(result, null, 2));
    })
    .catch((err) => {
      console.error("Scrape failed:", err instanceof Error ? err.message : err);
      process.exit(1);
    });
}
