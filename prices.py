# /// script
# requires-python = ">=3.12"
# dependencies = ["requests", "playwright", "tzdata"]
# ///
import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from playwright.async_api import async_playwright


TOP_N = 10
RANKINGS_URL = "https://openrouter.ai/rankings#programming-languages"

# Token assumptions for cost comparison (typical coding task):
#   input  = 2,000 tokens (short prompt with code context)
#   output = 4,000 tokens (extended code generation / explanation)
# Adjust these to match your actual usage pattern.
INPUT_TOKENS = 2_000
OUTPUT_TOKENS = 4_000

HTML_FILE = os.environ.get("OUTPUT_DIR", "") + "prices.html"
MD_FILE = os.environ.get("OUTPUT_DIR", "") + "prices.md"

TZ = ZoneInfo("Europe/Berlin")

# Scrape the LLM Leaderboard: top models by overall usage/spend.
SCRAPE_JS = """
() => {
    const results = [];
    const seen = new Set();
    const headings = Array.from(document.querySelectorAll('h2'));
    const heading = headings.find(h => h.textContent.trim() === 'LLM Leaderboard');
    if (!heading) return results;
    let container = heading.parentElement;
    for (let i = 0; i < 6; i++) container = container.parentElement;
    const links = Array.from(container.querySelectorAll('a[href]'));
    for (const link of links) {
        const href = link.getAttribute('href') || '';
        const parts = href.split('/').filter(Boolean);
        if (parts.length !== 2 || href.startsWith('http')) continue;
        const author = parts[0];
        const slug = parts[1];
        const key = author + '/' + slug;
        if (seen.has(key)) continue;
        seen.add(key);
        const name = link.textContent.trim();
        if (!name) continue;
        results.push({ model_id: key, name: name, author: author });
    }
    return results.slice(0, %d);
}
""" % TOP_N


def get_timestamp():
    """Return the current timestamp in Europe/Berlin timezone."""
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def fetch_openrouter_prices():
    """Fetch all current pricing data from the official OpenRouter API."""
    response = requests.get("https://openrouter.ai/api/v1/models")
    if response.status_code == 200:
        return response.json().get("data", [])
    return []


def build_pricing_lookup(models_api_data):
    """Build a dict mapping model ID -> pricing for fast lookup."""
    lookup = {}
    for m in models_api_data:
        pricing = m.get("pricing", {})
        prompt_p = float(pricing.get("prompt", 0)) * 1_000_000
        comp_p = float(pricing.get("completion", 0)) * 1_000_000
        lookup[m["id"].lower()] = (m["id"], prompt_p, comp_p)
    return lookup


def find_pricing(lookup, model_id):
    """Find pricing with fallback: exact match -> try without :free -> partial match.
    
    For :free models, only fall back to the base model if it's also free.
    If the base model has paid pricing, return None (the free variant is a
    separate offering rather than the paid model).
    """
    mid = model_id.lower()

    # 1) Exact lookup
    if mid in lookup:
        return lookup[mid]

    # 2) Try without :free suffix (e.g. "tencent/hy3:free" -> "tencent/hy3")
    base, _, suffix = mid.rpartition(":")
    matched = lookup.get(base)
    if matched:
        # Only use the base model if it's free (prompt价 and completion价 are both 0)
        if suffix == "free" and (matched[1] > 0 or matched[2] > 0):
            return None
        return matched

    # 3) Try partial match: model ID starts with an existing key
    for key, val in lookup.items():
        if key.startswith(mid):
            return val

    return None


async def main():
    print("1. Launching browser and loading rankings...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(RANKINGS_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        items = await page.evaluate(SCRAPE_JS)
        await browser.close()

    print(f"2. Found {len(items)} top models.\n")

    print("3. Fetching pricing data from OpenRouter API...\n")
    api_models = fetch_openrouter_prices()
    pricing_lookup = build_pricing_lookup(api_models)

    # Build rows with pricing + value score
    rows = []
    for i, item in enumerate(items, start=1):
        model_id = item["model_id"]
        matched = find_pricing(pricing_lookup, model_id)

        if matched:
            _, prompt_price, comp_price = matched
            if prompt_price == 0 and comp_price == 0:
                # Free model
                prompt_str = "Free"
                comp_str = "Free"
                cost = 0
            else:
                prompt_str = f"${prompt_price:.2f}"
                comp_str = f"${comp_price:.2f}"
                cost = (prompt_price * INPUT_TOKENS / 1_000_000
                        + comp_price * OUTPUT_TOKENS / 1_000_000)
        else:
            prompt_str = comp_str = "N/A"
            prompt_price = comp_price = cost = 0

        # Value score: lower cost + higher rank = better value.
        # Free models get infinite boost; paid models scored by 1/cost.
        # Unknown models (N/A) get a neutral score (no boost, no penalty).
        if cost > 0:
            value = (TOP_N + 1 - i) / cost
        elif matched:
            value = float('inf')
        else:
            value = 0

        rows.append({
            "value": value,
            "name": item["name"],
            "author": item["author"],
            "input": prompt_str,
            "output": comp_str,
            "cost": f"${cost:.6f}" if cost > 0 else ("Free" if matched else "N/A"),
            "rank": i,
        })

    rows.sort(key=lambda r: r["value"], reverse=True)

    # --- Guardrail: warn if pricing coverage is too low ---
    matched_count = sum(1 for r in rows if r["cost"] not in ("N/A", "Free"))
    if matched_count == 0:
        print("\nERROR: Could not resolve pricing for ANY model.")
        print("This usually means the OpenRouter API returned no pricing data")
        print("or the page structure has changed. Please check manually at:")
        print(f"  {RANKINGS_URL}")
        print(f"  https://openrouter.ai/api/v1/models")
        # Still generate output, but mark as anomalous
    elif matched_count < len(rows) // 3:
        print(f"\nWARNING: Only {matched_count} of {len(rows)} models have pricing data.")
        print("The OpenRouter API may have changed. Verify at:")
        print(f"  https://openrouter.ai/api/v1/models")

    # --- Print to console ---
    sep = "=" * 120
    hdr = (f"{'#':<4} | {'Model':<28} | {'Author':<12} "
           f"| {'Input / 1M':<12} | {'Output / 1M':<12} "
           f"| {'Cost (2k in + 4k out)':<22} | {'Orig Rank'}")
    print(sep)
    print(hdr)
    print(sep)

    for i, r in enumerate(rows, start=1):
        print(
            f"{i:<4} | {r['name']:<28} | {r['author']:<12} "
            f"| {r['input']:<12} | {r['output']:<12} "
            f"| {r['cost']:<22} | {r['rank']}"
        )

    print(sep)
    print(f"\n(*) Cost calculated for {INPUT_TOKENS:,} input tokens + {OUTPUT_TOKENS:,} output tokens")
    print(f"    Prices are per 1M tokens on OpenRouter.")
    print(f"    {matched_count} models with full pricing, {sum(1 for r in rows if r['input'] == 'Free')} free, {sum(1 for r in rows if r['input'] == 'N/A')} with no pricing data.")

    # --- Generate Markdown file ---
    generate_markdown(rows)

    # --- Generate HTML file ---
    generate_html(rows)


def generate_markdown(rows):
    """Write results as a Markdown table."""
    ts = get_timestamp()
    lines = [
        "# OpenRouter Programming Models — Value for Money\n",
        f"*Generated: {ts}*\n",
        f"*Data scraped from the [OpenRouter Rankings — Programming](https://openrouter.ai/rankings#programming-languages) section. "
        f"Cost calculated for {INPUT_TOKENS:,} input + {OUTPUT_TOKENS:,} output tokens per task.*\n",
        "## Rankings (sorted by value)\n",
    ]

    lines.append("| # | Model | Author | Input / 1M | Output / 1M | Cost per task | Orig Rank |")
    lines.append("|---|-------|--------|------------|-------------|---------------|-----------|")

    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {r['name']} | {r['author']} | {r['input']} | {r['output']} | {r['cost']} | {r['rank']} |"
        )

    lines.append(f"\n---\n*Prices are per 1M tokens on OpenRouter. "
                 f"Cost = ({INPUT_TOKENS:,} × input/1M) + ({OUTPUT_TOKENS:,} × output/1M).*\n")

    with open(MD_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n3a. Markdown written to {MD_FILE}")


def generate_html(rows):
    """Write results as a styled HTML table."""
    cost_desc = f"{INPUT_TOKENS:,} input + {OUTPUT_TOKENS:,} output"
    ts = get_timestamp()

    html_rows = ""
    for i, r in enumerate(rows, start=1):
        css_class = "free" if r["cost"] == "Free" else ""
        html_rows += f"""        <tr class="{css_class}">
          <td>{i}</td>
          <td>{r['name']}</td>
          <td>{r['author']}</td>
          <td>{r['input']}</td>
          <td>{r['output']}</td>
          <td>{r['cost']}</td>
          <td>{r['rank']}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenRouter Programming Models — Value for Money</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 1100px;
    margin: 2rem auto;
    padding: 0 1rem;
    background: #0d1117;
    color: #c9d1d9;
  }}
  h1 {{ color: #58a6ff; margin-bottom: 0.5rem; }}
  .subtitle {{ color: #8b949e; margin-bottom: 1.5rem; font-size: 0.95rem; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }}
  th {{
    background: #161b22;
    color: #58a6ff;
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid #30363d;
    white-space: nowrap;
  }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid #21262d;
  }}
  tr:hover td {{ background: #161b22; }}
  tr.free td {{ color: #3fb950; }}
  tr.free td:first-child {{ font-weight: bold; color: #3fb950; }}
  .note {{
    margin-top: 1rem;
    font-size: 0.85rem;
    color: #8b949e;
  }}
  .note a {{ color: #58a6ff; text-decoration: none; }}
  .note a:hover {{ text-decoration: underline; }}
  td:nth-child(6) {{ font-family: monospace; }}
</style>
</head>
<body>
  <h1>OpenRouter Programming Models — Value for Money</h1>
  <p class="subtitle">Data scraped from
    <a href="https://openrouter.ai/rankings#programming-languages" style="color:#58a6ff">OpenRouter Rankings — Programming</a> section.
    Cost calculated for {cost_desc} tokens per task.
  </p>
  <p class="subtitle">Generated: {ts}</p>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Model</th>
        <th>Author</th>
        <th>Input / 1M</th>
        <th>Output / 1M</th>
        <th>Cost per task</th>
        <th>Orig Rank</th>
      </tr>
    </thead>
    <tbody>
{html_rows}
    </tbody>
  </table>
  <p class="note">Prices are per 1M tokens on OpenRouter.
    Cost = ({INPUT_TOKENS:,} × input/1M) + ({OUTPUT_TOKENS:,} × output/1M).
  </p>
</body>
</html>
"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"3b. HTML written to {HTML_FILE}")


if __name__ == "__main__":
    asyncio.run(main())