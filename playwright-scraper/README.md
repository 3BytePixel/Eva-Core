# playwright-scraper

Local browser automation with [Playwright](https://playwright.dev/) — no cloud
service or credentials required. The `scrape` command launches a local headless
Chromium, loads a URL, and returns the page `title` plus optional text extracted
for a CSS `selector`. It can also save a full-page screenshot.

## Setup

```bash
pnpm install
pnpm browser:install   # downloads the Chromium browser used by Playwright
```

On Linux you may also need system libraries once:

```bash
pnpm exec playwright install-deps chromium   # uses apt; may require sudo
```

## Usage

```bash
pnpm scrape <url> [--selector <css>] [--screenshot <path>] [--timeout <ms>] [--headed]
```

Examples:

```bash
pnpm scrape https://example.com --selector h1
pnpm scrape https://news.ycombinator.com --selector ".titleline > a" --screenshot hn.png
```

Output is JSON, e.g.:

```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "selector": "h1",
  "count": 1,
  "items": ["Example Domain"],
  "screenshot": null,
  "timestamp": "..."
}
```

## Develop

```bash
pnpm typecheck   # tsc --noEmit
pnpm test        # smoke test against example.com
```

`scrape.ts` also exports `scrape(options)` so it can be imported and used
programmatically.
