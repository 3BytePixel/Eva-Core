# browser-functions

A [Browserbase Function](https://browserbase.com/docs) — serverless browser
automation deployed to the Browserbase cloud and invoked via HTTP.

The function `scrape-page` loads a URL in a cloud Chromium session, returns the
page `title`, and (optionally) extracts text for a CSS `selector`.

## Prerequisites

Get an API key + Project ID at <https://browserbase.com/settings>, then:

```bash
cp .env.example .env   # fill in BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID
pnpm install
```

## Local development

```bash
pnpm dev        # bb dev index.ts  → http://127.0.0.1:14113
```

Invoke it locally:

```bash
curl -X POST http://127.0.0.1:14113/v1/functions/scrape-page/invoke \
  -H "Content-Type: application/json" \
  -d '{"params": {"url": "https://example.com", "selector": "h1"}}'
```

## Deploy

```bash
pnpm publish    # bb publish index.ts  → prints a Function ID
```

Invoke the deployed function:

```bash
curl -X POST "https://api.browserbase.com/v1/functions/FUNCTION_ID/invoke" \
  -H "Content-Type: application/json" \
  -H "x-bb-api-key: $BROWSERBASE_API_KEY" \
  -d '{"params": {"url": "https://example.com"}}'
# → {"id": "INVOCATION_ID"}; then poll:
curl "https://api.browserbase.com/v1/functions/invocations/INVOCATION_ID" \
  -H "x-bb-api-key: $BROWSERBASE_API_KEY"
```

## Params

| Param       | Type   | Required | Description                                   |
| ----------- | ------ | -------- | --------------------------------------------- |
| `url`       | string | yes      | Page to load                                  |
| `selector`  | string | no       | CSS selector to wait for and extract text     |
| `timeoutMs` | number | no       | Navigation / selector timeout (default 30000) |
