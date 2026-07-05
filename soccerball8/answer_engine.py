"""Ties Ollama + the fact-checker together to produce the final on-screen answer."""

import json
from dataclasses import dataclass
from typing import Optional

from .config import Settings
from .fact_check import FactCheckResult, fact_check
from .ollama_client import OllamaClient

_CLAIM_SYSTEM = (
    "You turn a yes/no style question into a single, searchable factual CLAIM "
    "written as a plain declarative statement, plus a short web search QUERY. "
    'Respond in strict JSON: {"claim": "...", "query": "..."}. '
    "If the question is a matter of opinion, a prediction of random luck, or has "
    'no factual answer that could be looked up, respond instead with '
    '{"claim": null, "query": null}. Respond with JSON only, no other text.'
)

_PHRASING_SYSTEM = (
    "You are the oracle inside a soccer-themed Magic 8-Ball. Reply with a short "
    "(under 60 characters) punchy, single-sentence answer in classic Magic "
    "8-Ball style, themed around scoring a goal. Do not explain yourself, "
    "just give the line that should appear on screen."
)

_UNKNOWN_TEXT = "I don't know - the evidence isn't clear enough to call that one."


@dataclass
class Answer:
    text: str
    verdict: str  # "yes" | "no" | "unknown"
    confidence: float
    fact_check: Optional[FactCheckResult]


def _extract_claim(ollama: OllamaClient, question: str):
    raw = ollama.generate(question, system=_CLAIM_SYSTEM, temperature=0.0)
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        data = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return None, None
    return data.get("claim"), data.get("query")


def answer_question(question: str, ollama: OllamaClient, settings: Settings) -> Answer:
    claim, query = _extract_claim(ollama, question)

    if not claim or not query:
        text = ollama.generate(
            f'Question: "{question}"\nThis has no factual answer to look up. '
            "Give a playful Magic 8-Ball style answer.",
            system=_PHRASING_SYSTEM,
        )
        return Answer(text, "unknown", 0.0, None)

    result = fact_check(
        claim,
        query,
        ollama,
        settings.google_api_key,
        settings.google_cse_id,
        settings.search_results,
        settings.min_relevant_results,
        settings.confidence_threshold,
    )

    if result.verdict == "unknown":
        return Answer(_UNKNOWN_TEXT, "unknown", result.confidence, result)

    verdict_hint = "YES, this is true" if result.verdict == "yes" else "NO, this is false"
    prompt = (
        f'Question: "{question}"\n'
        f"Fact-check verdict: {verdict_hint} (confidence {result.confidence:.0%}).\n"
        "Give the final answer."
    )
    text = ollama.generate(prompt, system=_PHRASING_SYSTEM)
    return Answer(text, result.verdict, result.confidence, result)
