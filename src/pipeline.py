from __future__ import annotations

from datetime import datetime
from pathlib import Path

KEYWORDS = [
    # Core roles
    "Data scientist",
    "Machine learning",
    "Machine learning engineer",
    "AI engineer",
    "Data engineer",
    "Analytics engineer",
    # Bioinformatics / life science
    "Bioinformatics",
    "Computational biology",
    "Genomics",
    "Life science data",
    # Deep learning / generative
    "Deep learning",
    "Generative AI",
    "NLP",
    "Computer vision",
    # MLOps / infra
    "MLOps",
    "Data platform",
    # Consulting / applied
    "AI konsulent",
    "Data analyst",
    "Quantitative analyst",
]

REFERENCES_DIR = Path(__file__).parent.parent / "references"

DEFAULT_LOCAL_MODEL = "llama3.2"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


def load_references() -> str:
    refs = []
    for path in sorted(REFERENCES_DIR.glob("*.md")):
        refs.append(f"--- Example: {path.name} ---\n{path.read_text()}")
    return "\n\n".join(refs)


def scrape_all(max_per_keyword: int = 20) -> list[dict]:
    from src.scraper import scrape_jobnet

    seen_ids: set[str] = set()
    all_jobs: list[dict] = []

    for keyword in KEYWORDS:
        print(f"  Scraping {keyword!r} ...")
        jobs = scrape_jobnet(keyword, max_results=max_per_keyword)
        for job in jobs:
            job_id = job["id"]
            if job_id not in seen_ids:
                seen_ids.add(job_id)
                all_jobs.append(job)

    return all_jobs


def _build_prompt(job: dict, references: str) -> tuple[str, str]:
    my_info_path = REFERENCES_DIR / "my_info.md"
    my_info = my_info_path.read_text() if my_info_path.exists() else ""

    system = (
        "You are a job-match assistant. You are given examples of job postings that "
        "a candidate found interesting. Based on these examples, decide whether a new "
        "job posting is a good match.\n\n"
        "IMPORTANT — no studend postions\n"
        "IMPORTANT — Candidate personal info and preferences (pay close attention to this):\n"
        f"{my_info}\n\n"
        "Respond using exactly this format:\n"
        "MATCH: yes/no\n"
        "SCORE: 1-10\n"
        "REASON: one or two sentences.\n\n"
        "Examples of good postings: you should really try to match postings with these postings!!!:\n\n"
        f"{references}"
    )

    user = (
        "Is the following job a good match?\n\n"
        f"Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Description: {job['description']}\n"
        f"URL: {job['url']}"
    )
    return system, user


def _parse_response(text: str) -> tuple[bool, int]:
    lower = text.lower()
    match = False
    if "match:" in lower:
        match_line = lower.split("match:")[1].split("\n")[0]
        match = "yes" in match_line

    score = 0
    for line in lower.splitlines():
        if line.startswith("score:"):
            digits = "".join(c for c in line.split(":", 1)[1] if c.isdigit())[:2]
            try:
                score = int(digits)
            except ValueError:
                pass
            break

    return match, score


def evaluate_job_remote(job: dict, references: str, model: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    system, user = _build_prompt(job, references)

    message = client.messages.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = message.content[0].text
    match, score = _parse_response(text)
    return {**job, "match": match, "score": score, "llm_response": text}


def evaluate_job_local(job: dict, references: str, model: str) -> dict:
    from openai import OpenAI

    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    system, user = _build_prompt(job, references)

    response = client.chat.completions.create(
        model=model,
        max_tokens=512,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    match, score = _parse_response(text)
    return {**job, "match": match, "score": score, "llm_response": text}


def evaluate_job_openai(job: dict, references: str, model: str) -> dict:
    from openai import OpenAI

    client = OpenAI()
    system, user = _build_prompt(job, references)

    response = client.chat.completions.create(
        model=model,
        max_tokens=512,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = response.choices[0].message.content or ""
    match, score = _parse_response(text)
    return {**job, "match": match, "score": score, "llm_response": text}


_DEFAULTS = {
    "local": DEFAULT_LOCAL_MODEL,
    "anthropic": DEFAULT_ANTHROPIC_MODEL,
    "openai": DEFAULT_OPENAI_MODEL,
}

_EVALUATORS = {
    "local": evaluate_job_local,
    "anthropic": evaluate_job_remote,
    "openai": evaluate_job_openai,
}


def run_pipeline(
    llm: str = "local",
    model: str | None = None,
    max_per_keyword: int = 20,
    min_score: int = 4,
) -> list[dict]:
    resolved_model = model or _DEFAULTS[llm]
    evaluate = _EVALUATORS[llm]

    print(f"Backend : {llm}  |  Model: {resolved_model}\n")

    references = load_references()
    if not references:
        print("Warning: no reference files found in references/\n")

    print("Scraping jobs ...")
    jobs = scrape_all(max_per_keyword=max_per_keyword)
    print(f"Unique jobs found: {len(jobs)}\n")

    matches = []
    for i, job in enumerate(jobs, 1):
        print(f"[{i}/{len(jobs)}] {job['title']} @ {job['company']}")
        result = evaluate(job, references, resolved_model)
        if result["match"] and result["score"] >= min_score:
            matches.append(result)

    matches.sort(key=lambda x: x["score"], reverse=True)
    save_report(matches[:10])
    return matches


def save_report(matches: list[dict]) -> None:
    reports_dir = Path(__file__).parent.parent / "reports"
    filename = reports_dir / f"{datetime.now().strftime('%d-%m-%Y')}.md"

    lines = [f"# Job matches — {datetime.now().strftime('%d-%m-%Y')}\n"]
    for i, job in enumerate(matches, 1):
        reason = job["llm_response"].split("REASON:", 1)[-1].strip()
        lines.append(f"## {i}. [{job['title']} @ {job['company']}]({job['url']})")
        lines.append(f"{reason}")
        lines.append(f"- **URL:** {job['url']}")
        lines.append(f"- **Deadline:** {job['deadline']}\n")

    filename.write_text("\n".join(lines))
    print(f"\nReport saved to {filename}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape and match jobs using an LLM.")
    parser.add_argument("--llm", choices=["local", "anthropic", "openai"], default="local")
    parser.add_argument("--model", default=None, help="Override default model name.")
    parser.add_argument("--max", type=int, default=20, dest="max_per_keyword", help="Max jobs per keyword.")
    parser.add_argument("--min-score", type=int, default=6, help="Minimum match score (1-10).")
    args = parser.parse_args()

    results = run_pipeline(
        llm=args.llm,
        model=args.model,
        max_per_keyword=args.max_per_keyword,
        min_score=args.min_score,
    )

    print(f"\n{'=' * 60}")
    print(f"MATCHES: {len(results)} job(s) found")
    print(f"{'=' * 60}\n")

    for job in results:
        print(f"[{job['score']}/10] {job['title']} @ {job['company']}")
        print(f"  Location : {job['location']}")
        print(f"  Deadline : {job['deadline']}")
        print(f"  URL      : {job['url']}")
        reason = job["llm_response"].split("REASON:", 1)[-1].strip()[:250]
        print(f"  Reason   : {reason}")
        print()
