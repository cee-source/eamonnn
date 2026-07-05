"""Cross-checks a claim against multiple independent Google search results.

Two independent signals are combined into a single confidence score:

1. Stance voting - each search result snippet is classified by the LLM as
   SUPPORTS / CONTRADICTS / UNRELATED to the claim, and we take the fraction
   of relevant snippets that agree with each other.
2. Cross-snippet agreement - the supporting/contradicting snippets are
   compared *against each other* (not just against the claim) so that a
   single lucky/unlucky source can't dominate the verdict.

If there isn't enough relevant evidence, or the two results disagree, the
verdict comes back "unknown" rather than guessing.
"""

import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import List, Optional

from .ollama_client import OllamaClient
from .search import GoogleSearchError, search_google


@dataclass
class FactCheckResult:
    claim: str
    verdict: str  # "yes" | "no" | "unknown"
    confidence: float
    supports: int
    contradicts: int
    unrelated: int
    agreement_score: float
    evidence: List[dict] = field(default_factory=list)


def _word_set(text: str) -> set:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _cross_snippet_agreement(snippets: List[str]) -> float:
    """Average pairwise similarity between relevant snippets - how much do
    independent Google results corroborate each other, ignoring the claim."""
    word_sets = [_word_set(s) for s in snippets if s]
    if len(word_sets) < 2:
        return 0.0
    scores = [_jaccard(a, b) for a, b in combinations(word_sets, 2)]
    return sum(scores) / len(scores)


_CLASSIFY_SYSTEM = (
    "You are a strict fact-checking classifier. Given a CLAIM and a short SNIPPET "
    "of search-result text, decide whether the snippet SUPPORTS the claim, "
    "CONTRADICTS the claim, or is UNRELATED (not enough information). "
    "Respond with exactly one word: SUPPORTS, CONTRADICTS, or UNRELATED."
)


def _classify_snippet(client: OllamaClient, claim: str, snippet: str) -> str:
    prompt = f"CLAIM: {claim}\nSNIPPET: {snippet}\nAnswer:"
    raw = client.generate(prompt, system=_CLASSIFY_SYSTEM, temperature=0.0)
    verdict = raw.strip().splitlines()[0].strip().upper()
    for label in ("SUPPORTS", "CONTRADICTS", "UNRELATED"):
        if label in verdict:
            return label
    return "UNRELATED"


def fact_check(
    claim: str,
    search_query: str,
    ollama: OllamaClient,
    google_api_key: str,
    google_cse_id: str,
    num_results: int = 8,
    min_relevant: int = 3,
    confidence_threshold: float = 0.7,
) -> FactCheckResult:
    try:
        results = search_google(search_query, google_api_key, google_cse_id, num_results)
    except GoogleSearchError:
        return FactCheckResult(claim, "unknown", 0.0, 0, 0, 0, 0.0, [])

    supports = contradicts = unrelated = 0
    evidence = []
    for result in results:
        snippet = f"{result['title']}. {result['snippet']}"
        label = _classify_snippet(ollama, claim, snippet)
        evidence.append({**result, "verdict": label})
        if label == "SUPPORTS":
            supports += 1
        elif label == "CONTRADICTS":
            contradicts += 1
        else:
            unrelated += 1

    relevant = supports + contradicts
    agreement = _cross_snippet_agreement(
        [e["snippet"] for e in evidence if e["verdict"] in ("SUPPORTS", "CONTRADICTS")]
    )

    if relevant < min_relevant:
        return FactCheckResult(claim, "unknown", 0.0, supports, contradicts, unrelated, agreement, evidence)

    stance_probability = supports / relevant
    # Blend "do the relevant results lean one way" with "do they actually
    # corroborate each other" so a single confident-sounding source can't
    # swing the verdict on its own.
    confidence = 0.7 * max(stance_probability, 1 - stance_probability) + 0.3 * agreement

    if confidence < confidence_threshold:
        verdict = "unknown"
    elif stance_probability >= 0.5:
        verdict = "yes"
    else:
        verdict = "no"

    return FactCheckResult(claim, verdict, confidence, supports, contradicts, unrelated, agreement, evidence)
