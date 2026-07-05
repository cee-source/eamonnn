from soccerball8.fact_check import FactCheckResult, _cross_snippet_agreement, _jaccard, fact_check
from soccerball8.search import GoogleSearchError


def test_jaccard_identical_sets():
    a = {"messi", "scored", "goal"}
    assert _jaccard(a, a) == 1.0


def test_jaccard_disjoint_sets():
    assert _jaccard({"messi"}, {"ronaldo"}) == 0.0


def test_jaccard_empty_set_is_zero():
    assert _jaccard(set(), {"messi"}) == 0.0


def test_cross_snippet_agreement_needs_two_snippets():
    assert _cross_snippet_agreement(["only one snippet here"]) == 0.0


def test_cross_snippet_agreement_rewards_overlap():
    identical = _cross_snippet_agreement(["messi scored a goal", "messi scored a goal"])
    disjoint = _cross_snippet_agreement(["messi scored a goal", "completely unrelated text"])
    assert identical > disjoint


def test_fact_check_returns_unknown_when_search_unavailable(monkeypatch):
    def _boom(*args, **kwargs):
        raise GoogleSearchError("no api key")

    monkeypatch.setattr("soccerball8.fact_check.search_google", _boom)

    class _NoCallOllama:
        def generate(self, *args, **kwargs):  # pragma: no cover - should not be called
            raise AssertionError("should not classify snippets if search failed")

    result = fact_check("claim", "query", _NoCallOllama(), "key", "cse")
    assert isinstance(result, FactCheckResult)
    assert result.verdict == "unknown"


def test_fact_check_unknown_when_evidence_too_thin(monkeypatch):
    monkeypatch.setattr(
        "soccerball8.fact_check.search_google",
        lambda *a, **k: [{"title": "t1", "snippet": "s1", "link": "l1"}],
    )

    class _UnrelatedOllama:
        def generate(self, *args, **kwargs):
            return "UNRELATED"

    result = fact_check(
        "claim", "query", _UnrelatedOllama(), "key", "cse", min_relevant=3
    )
    assert result.verdict == "unknown"


def test_fact_check_yes_when_all_support(monkeypatch):
    monkeypatch.setattr(
        "soccerball8.fact_check.search_google",
        lambda *a, **k: [
            {"title": "t1", "snippet": "messi scored a hat trick in the final", "link": "l1"},
            {"title": "t2", "snippet": "messi scored a hat trick in the final match", "link": "l2"},
            {"title": "t3", "snippet": "messi scored a hat trick during the final", "link": "l3"},
        ],
    )

    class _SupportsOllama:
        def generate(self, *args, **kwargs):
            return "SUPPORTS"

    result = fact_check(
        "Messi scored a hat trick in the final", "query", _SupportsOllama(),
        "key", "cse", min_relevant=3, confidence_threshold=0.7,
    )
    assert result.verdict == "yes"
    assert result.confidence >= 0.7
