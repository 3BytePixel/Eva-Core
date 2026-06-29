import assert from "node:assert/strict";

import { scrape } from "../scrape.ts";

async function main() {
  console.log("Smoke test: scraping https://example.com ...");
  const result = await scrape({ url: "https://example.com", selector: "h1" });

  assert.equal(result.url, "https://example.com");
  assert.match(result.title, /Example Domain/i);
  assert.ok(result.items && result.items.length >= 1, "expected at least one <h1>");
  assert.match(result.items![0], /Example Domain/i);

  console.log("PASS:", JSON.stringify(result));
}

main().catch((err) => {
  console.error("FAIL:", err);
  process.exit(1);
});
