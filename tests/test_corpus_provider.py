from pdd_agent.drafting.corpus_provider import CorpusProvider
from pdd_agent.retrieval.search import RetrievalResult


def _result(text="A" * 200):
    return RetrievalResult(
        "3", "3.4", "reference-pdd", "Baseline Scenario", text,
        "NARRATIVE", "MEDIUM", 1.0, [],
    )


def test_adapts_full_corpus_text_with_marker():
    provider = CorpusProvider(retrieval=lambda *args, **kwargs: [_result()])
    draft = provider.draft_section("3", "3.4", "prompt", [], max_chars=1000)
    assert "[ADAPTED FROM CORPUS: reference-pdd]" in draft.text
    assert draft.provider == "corpus"
    assert draft.provenance[-1].startswith("[CORPUS:")


def test_falls_back_when_retrieval_is_empty():
    provider = CorpusProvider(retrieval=lambda *args, **kwargs: [])
    draft = provider.draft_section("3", "3.4", "prompt", [], max_chars=1000)
    assert "[SYNTHETIC FALLBACK:" in draft.text
