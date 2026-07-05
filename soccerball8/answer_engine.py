"""Turns a fact-check verdict into a short Magic-8-Ball-style line.

No AI/LLM involved - just the keyword-based fact_check() result and a bank
of canned phrases, so there's no per-question cost and nothing to run or
license beyond the free Google Custom Search quota.
"""

import random
from dataclasses import dataclass
from typing import Optional

from .config import Settings
from .fact_check import FactCheckResult, fact_check

_YES_PHRASES = [
    "GOAL! Yes, without a doubt.",
    "Back of the net -- it's a yes.",
    "Onside and onward: yes.",
    "The net ripples -- signs point to yes.",
    "Top corner, keeper's got no chance. Yes.",
]

_NO_PHRASES = [
    "Saved! The answer is no.",
    "Offside -- don't count on it.",
    "Wide of the post: no.",
    "The keeper's got this one. No.",
    "Crossbar denies it. No.",
]

_UNKNOWN_PHRASES = [
    "I don't know -- the evidence isn't clear enough to call it.",
    "VAR is still checking. I don't know.",
    "Too foggy to call. I don't know.",
    "The whistle hasn't blown yet -- I don't know.",
]


@dataclass
class Answer:
    text: str
    verdict: str  # "yes" | "no" | "unknown"
    confidence: float
    fact_check: Optional[FactCheckResult]


def answer_question(question: str, settings: Settings) -> Answer:
    result = fact_check(
        question,
        settings.google_api_key,
        settings.google_cse_id,
        settings.search_results,
        settings.min_relevant_results,
        settings.confidence_threshold,
    )

    if result.verdict == "yes":
        text = random.choice(_YES_PHRASES)
    elif result.verdict == "no":
        text = random.choice(_NO_PHRASES)
    else:
        text = random.choice(_UNKNOWN_PHRASES)

    return Answer(text, result.verdict, result.confidence, result)
