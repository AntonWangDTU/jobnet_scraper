# Job Search Pipeline

Automated job scraper and LLM-based matcher for [Jobnet.dk](https://jobnet.dk). Scrapes postings by keyword, scores each one against your profile and example references, and saves a ranked report of the best matches.

## How it works

1. **Scrape** — Playwright fetches job postings from Jobnet.dk for each configured keyword, intercepting the XHR API responses to extract structured data.
2. **Evaluate** — Each job is sent to an LLM with your personal profile (`references/my_info.md`) and example good postings (`references/*.md`) as context. The model returns a match decision, a score (1–10), and a short reason.
3. **Report** — Matches above the minimum score threshold are ranked and saved to `reports/DD-MM-YYYY.md`.

## Setup

**Install dependencies:**
```bash
uv sync
playwright install chromium
```

**Configure your profile** by editing:
- `references/my_info.md` — your background, skills, and preferences
- `references/*.md` — example job postings you consider a good match (used as few-shot examples)

**Set API keys** as environment variables if using a remote backend:
```bash
export ANTHROPIC_API_KEY=...   # for --llm anthropic
export OPENAI_API_KEY=...      # for --llm openai
```

## Usage

```bash
uv run python src/pipeline.py [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--llm` | `local` | Backend: `local` (Ollama), `anthropic`, or `openai` |
| `--model` | see below | Override the default model for the chosen backend |
| `--max` | `20` | Max job postings scraped per keyword |
| `--min-score` | `6` | Minimum LLM score (1–10) to include in report |

**Default models:**
- `local` → `llama3.2` (requires [Ollama](https://ollama.com) running locally)
- `anthropic` → `claude-sonnet-4-6`
- `openai` → `gpt-4o-mini`

**Examples:**
```bash
# Run with local Ollama model
uv run python src/pipeline.py

# Run with Claude, stricter score threshold
uv run python src/pipeline.py --llm anthropic --min-score 7

# Run with OpenAI, more results per keyword
uv run python src/pipeline.py --llm openai --max 40
```

Or use the shorthand poe task:
```bash
uv run poe run
```

## Project structure

```
references/
  my_info.md       # Your profile and matching preferences
  1.md, 2.md ...   # Example job postings (few-shot context)
reports/
  DD-MM-YYYY.md    # Generated match reports
src/
  scraper.py       # Playwright-based Jobnet scraper
  pipeline.py      # LLM evaluation and report generation
```

## Keywords

Defined in `pipeline.py`:
```python
KEYWORDS = [
    "Data science",
    "Machine Learning",
    "Bioinformatics",
    "Machine learning engineer",
]
```

Edit this list to broaden or narrow the search.
