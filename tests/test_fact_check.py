from soccerball8.fact_check import (
    FactCheckResult,
    _classify_snippet,
    _containment,
    _cross_snippet_agreement,
    _jaccard,
    _keywords,
    fact_check,
)
from soccerball8.search import GoogleSearchError


def test_keywords_strips_stopwords():
    kw = _keywords("Did Messi win the World Cup?")
    assert "messi" in kw
    assert "world" in kw
    assert "did" not in kw
    assert "the" not in kw


def test_jaccard_identical_sets():
    a = {"messi", "scored", "goal"}
    assert _jaccard(a, a) == 1.0


def test_jaccard_disjoint_sets():
    assert _jaccard({"messi"}, {"ronaldo"}) == 0.0


def test_containment_full_match():
    question_keywords = {"messi", "world", "cup"}
    snippet_words = {"messi", "world", "cup", "final", "argentina"}
    assert _containment(question_keywords, snippet_words) == 1.0


def test_containment_no_overlap():
    assert _containment({"messi"}, {"ronaldo", "portugal"}) == 0.0


def test_classify_snippet_unrelated_below_threshold():
    question_keywords = _keywords("Did Messi win the World Cup?")
    label = _classify_snippet(question_keywords, "Completely unrelated text about cooking pasta.")
    assert label == "UNRELATED"


def test_classify_snippet_supports():
    question_keywords = _keywords("Did Messi win the World Cup?")
    label = _classify_snippet(question_keywords, "Messi won the World Cup with Argentina in 2022.")
    assert label == "SUPPORTS"


def test_classify_snippet_contradicts_on_negation():
    question_keywords = _keywords("Did Messi win the World Cup?")
    label = _classify_snippet(question_keywords, "Messi did not win the World Cup in 2018.")
    assert label == "CONTRADICTS"


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

    result = fact_check("Did Messi win the World Cup?", "key", "cse")
    assert isinstance(result, FactCheckResult)
    assert result.verdict == "unknown"


def test_fact_check_unknown_when_evidence_too_thin(monkeypatch):
    monkeypatch.setattr(
        "soccerball8.fact_check.search_google",
        lambda *a, **k: [{"title": "t1", "snippet": "completely unrelated text", "link": "l1"}],
    )

    result = fact_check("Did Messi win the World Cup?", "key", "cse", min_relevant=3)
    assert result.verdict == "unknown"


def test_fact_check_yes_when_all_support(monkeypatch):
    monkeypatch.setattr(
        "soccerball8.fact_check.search_google",
        lambda *a, **k: [
            {"title": "t1", "snippet": "Messi won the World Cup with Argentina", "link": "l1"},
            {"title": "t2", "snippet": "Messi won the World Cup in Qatar 2022", "link": "l2"},
            {"title": "t3", "snippet": "Messi and Argentina won the World Cup", "link": "l3"},
        ],
    )

    result = fact_check(
        "Did Messi win the World Cup?", "key", "cse", min_relevant=3, confidence_threshold=0.6
    )
    assert result.verdict == "yes"
    assert result.confidence >= 0.6


def test_fact_check_no_when_all_contradict(monkeypatch):
    monkeypatch.setattr(
        "soccerball8.fact_check.search_google",
        lambda *a, **k: [
            {"title": "t1", "snippet": "Messi did not win the World Cup in 2018", "link": "l1"},
            {"title": "t2", "snippet": "Messi did not win the World Cup that year", "link": "l2"},
            {"title": "t3", "snippet": "Messi never won the World Cup before 2022", "link": "l3"},
        ],
    )

    result = fact_check(
        "Did Messi win the World Cup?", "key", "cse", min_relevant=3, confidence_threshold=0.6
    )
    assert result.verdict == "no"
