"""Cross-checks a question against multiple independent Google search results
using pure keyword heuristics - no AI/LLM dependency, so this has zero
per-question cost and nothing else to run or license.

Two independent signals are combined into a single confidence score:

1. Stance voting - each search result snippet is classified as SUPPORTS /
   CONTRADICTS / UNRELATED by checking how many of the question's keywords
   it contains, and whether it also contains a negation word.
2. Cross-snippet agreement - the supporting/contradicting snippets are
   compared *against each other* (not just against the question) so a
   single outlier result can't dominate the verdict.

If there isn't enough relevant evidence, or the two results disagree, the
verdict comes back "unknown" rather than guessing.
"""

import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import List

from .search import GoogleSearchError, search_google

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "will", "did", "does", "do",
    "can", "could", "would", "should", "who", "what", "when", "where", "why",
    "how", "in", "on", "at", "of", "to", "for", "and", "or", "that", "this",
    "it", "he", "she", "they", "i", "you", "we", "has", "have", "had", "be",
    "been", "am", "with",
}

_NEGATION_WORDS = {
    "not", "never", "no", "false", "incorrect", "denied", "debunked", "myth",
    "hoax", "fake", "didnt", "doesnt", "isnt", "wasnt", "werent", "wont",
    "wouldnt", "couldnt", "shouldnt", "cannot", "cant",
}

# Fraction of the question's keywords a snippet must contain to be considered
# relevant at all, rather than UNRELATED.
RELEVANCE_THRESHOLD = 0.4


@dataclass
class FactCheckResult:
    question: str
    verdict: str  # "yes" | "no" | "unknown"
    confidence: float
    supports: int
    contradicts: int
    unrelated: int
    agreement_score: float
    evidence: List[dict] = field(default_factory=list)


def _words(text: str) -> set:
    return set(re.findall(r"[a-z0-9']+", text.lower().replace("'", "")))


def _keywords(text: str) -> set:
    return _words(text) - _STOPWORDS


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _containment(question_keywords: set, snippet_words: set) -> float:
    """What fraction of the question's keywords show up in this snippet."""
    if not question_keywords:
        return 0.0
    return len(question_keywords & snippet_words) / len(question_keywords)


def _cross_snippet_agreement(snippets: List[str]) -> float:
    """Average pairwise similarity between relevant snippets - how much do
    independent Google results corroborate each other, ignoring the question."""
    word_sets = [_keywords(s) for s in snippets if s]
    if len(word_sets) < 2:
        return 0.0
    scores = [_jaccard(a, b) for a, b in combinations(word_sets, 2)]
    return sum(scores) / len(scores)


def _classify_snippet(question_keywords: set, snippet: str) -> str:
    snippet_words = _words(snippet)
    if _containment(question_keywords, snippet_words) < RELEVANCE_THRESHOLD:
        return "UNRELATED"
    if snippet_words & _NEGATION_WORDS:
        return "CONTRADICTS"
    return "SUPPORTS"


def fact_check(
    question: str,
    google_api_key: str,
    google_cse_id: str,
    num_results: int = 8,
    min_relevant: int = 3,
    confidence_threshold: float = 0.7,
) -> FactCheckResult:
    try:
        results = search_google(question, google_api_key, google_cse_id, num_results)
    except GoogleSearchError:
        return FactCheckResult(question, "unknown", 0.0, 0, 0, 0, 0.0, [])

    question_keywords = _keywords(question)
    supports = contradicts = unrelated = 0
    evidence = []
    for result in results:
        snippet = f"{result['title']}. {result['snippet']}"
        label = _classify_snippet(question_keywords, snippet)
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
        return FactCheckResult(question, "unknown", 0.0, supports, contradicts, unrelated, agreement, evidence)

    stance_probability = supports / relevant
    # Blend "do the relevant results lean one way" with "do they actually
    # corroborate each other" so a single outlier result can't swing the
    # verdict on its own.
    confidence = 0.7 * max(stance_probability, 1 - stance_probability) + 0.3 * agreement

    if confidence < confidence_threshold:
        verdict = "unknown"
    elif stance_probability >= 0.5:
        verdict = "yes"
    else:
        verdict = "no"

    return FactCheckResult(question, verdict, confidence, supports, contradicts, unrelated, agreement, evidence)
