# openrouter-tools

A Python tool that scrapes the [OpenRouter Rankings — Programming](https://openrouter.ai/rankings#programming-languages) section for the most popular LLM coding models, fetches their pricing data via the OpenRouter API, and calculates the cost per task — outputting a single value-for-money ranked table.

## What it does

1. **Scrapes** the top 10 models from the [OpenRouter Rankings — Programming](https://openrouter.ai/rankings#programming-languages) section using Playwright
2. **Fetches** current pricing (per million tokens) from the OpenRouter API
3. **Calculates** cost for a typical coding task (configurable: default 2,000 input + 4,000 output tokens)
4. **Sorts** models by value-for-money (free models first, then by cost-adjusted rank)
5. **Outputs** results as:
   - Console table
   - Markdown file (`prices.md`)
   - HTML file (`prices.html`) with a dark theme

## Quick start

### Run locally with [uv](https://docs.astral.sh/uv/)

```bash
uv run prices.py
```

This installs dependencies automatically and runs the script. Output files (`prices.html`, `prices.md`) are written to the current directory.

### Run with Docker

```bash
docker build -t openrouter-prices .
docker run --rm -v "${PWD}:/app/output" openrouter-prices
```

Or use the helper scripts:

```powershell
.\run.ps1          # PowerShell (Windows)
```

```bash
./run.sh           # Bash (Linux / WSL / macOS)
```

This builds the Docker image, runs the container with a volume mount, and copies `prices.html` and `prices.md` to the current directory.

## Configuration

At the top of `prices.py` you can adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOP_N` | `10` | Number of top models to include |
| `INPUT_TOKENS` | `2,000` | Input tokens for cost calculation |
| `OUTPUT_TOKENS` | `4,000` | Output tokens for cost calculation |
| `RANKINGS_URL` | OpenRouter Rankings URL | Page to scrape |
| `HTML_FILE` | `prices.html` | Output HTML file |
| `MD_FILE` | `prices.md` | Output Markdown file |

## Output format

### Console (terminal)

```
========================================================================================================================
#    | Model                        | Author       | Input / 1M   | Output / 1M  | Cost (2k in + 4k out)  | Orig Rank
========================================================================================================================
1    | Hy3 (free)                   | tencent      | N/A          | N/A          | Free                   | 2
2    | Nemotron 3 Ultra (free)      | nvidia       | Free         | Free         | Free                   | 7
3    | DeepSeek V4 Flash            | deepseek     | $0.10        | $0.20        | $0.000980              | 3
...
```

### Markdown (`prices.md`)

```markdown
# OpenRouter Programming Models — Value for Money

*Generated: 2026-07-24 07:14:27 CEST*

*Data scraped from the [OpenRouter Rankings — Programming](https://openrouter.ai/rankings#programming-languages) section. Cost calculated for 2,000 input + 4,000 output tokens per task.*

## Rankings (sorted by value)

| # | Model | Author | Input / 1M | Output / 1M | Cost per task | Orig Rank |
|---|-------|--------|------------|-------------|---------------|-----------|
| 1 | Hy3 (free) | tencent | N/A | N/A | Free | 2 |
...
```

### HTML (`prices.html`)

A dark-themed HTML table with:
- Model name, author, input/output prices, per-task cost, and original rank
- Free models highlighted in green
- Width constrained to 1100px, responsive

## Project structure

```
openrouter-tools/
├── prices.py          # Main script (Python, ~280 lines)
├── Dockerfile         # Docker container (Python 3.14, Playwright)
├── run.ps1            # PowerShell helper: build → run → copy output
├── .dockerignore      # Docker build context exclusions
├── .gitignore         # Git exclusions
├── README.md          # This file
├── prices.html        # Generated HTML output
├── prices.md          # Generated Markdown output
└── output/            # Temporary Docker volume mount directory
```

## Dependencies

- **Python** ≥ 3.12
- **requests** — for fetching OpenRouter API data
- **playwright** — for scraping the rankings page
- **tzdata** — for timezone support (used for timestamps in output)

These are declared in the PEP 723 script metadata at the top of `prices.py` and are installed automatically by `uv run`.

## Docker details

The Dockerfile uses:
- `python:3.14-slim` base image
- Playwright browsers installed with system dependencies
- Output directory (`/app/output/`) for volume mount
- Entrypoint: `python prices.py`

Layer caching: dependencies are installed before the script is copied, so editing `prices.py` doesn't rebuild the expensive dependency layers.

## License

No license specified.
