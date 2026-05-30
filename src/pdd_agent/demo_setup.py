"""Demo environment setup: build a small FTS5 index from the bundled demo corpus.

The full corpus lives in `data/corpus/normalized/` (git-ignored). For the
one-command demos we ship a tiny public subset under `demo/corpus/` so colleagues
get corpus-backed provenance citations without ingesting the full corpus.

`build_demo_index()` builds `data/index/demo.fts.db` from that subset. The demo
index is a fallback: when the production `corpus.fts.db` is absent,
`get_retrieval_index()` (in `retrieval/index.py`) picks up `demo.fts.db`.
"""

from __future__ import annotations

import structlog
from pathlib import Path

from pdd_agent.retrieval.index import RetrievalIndex

logger = structlog.get_logger()

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_CORPUS_DIR = REPO_ROOT / "demo" / "corpus"
DEMO_INDEX_PATH = REPO_ROOT / "data" / "index" / "demo.fts.db"


def build_demo_index(
    demo_corpus_dir: Path | None = None,
    db_path: Path | None = None,
) -> RetrievalIndex:
    """Build the demo FTS5 index from the bundled demo corpus subset.

    Returns the built ``RetrievalIndex`` (already populated and queryable).
    Raises ``FileNotFoundError`` if the demo corpus directory is missing.
    """
    corpus_dir = Path(demo_corpus_dir) if demo_corpus_dir else DEMO_CORPUS_DIR
    index_path = Path(db_path) if db_path else DEMO_INDEX_PATH

    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Demo corpus not found at {corpus_dir}. "
            "Expected bundled normalized docs under demo/corpus/."
        )

    n_docs = len(list(corpus_dir.glob("*.norm.json")))
    index = RetrievalIndex(db_path=index_path)
    stats = index.build(normalized_dir=corpus_dir)

    logger.info(
        "demo_index_built",
        docs=stats.get("docs_indexed"),
        chunks=stats.get("chunks_indexed"),
        db_path=str(index_path),
    )
    print(
        f"Built demo index from {stats.get('docs_indexed', n_docs)} documents "
        f"in demo/corpus/ -> {index_path}"
    )
    return index
