import bm25s
from .parser import Chunk
from .models import MinimalSource

def build_bm25_index(chunks: list[Chunk], index_dir: str) -> None:
    """Tokenize every chunk, build the BM25 index, and persist it to disk."""
    texts = [chunk.content for chunk in chunks]
    metadata = [chunk.min_src.model_dump() for chunk in chunks]
    assert len(texts) == len(metadata)
    corpus_tokens = bm25s.tokenize(texts, stopwords=None, stemmer=None,
                                   show_progress=True)
    retriever = bm25s.BM25(corpus=metadata)
    retriever.index(corpus_tokens, show_progress=True)
    retriever.save(index_dir, corpus=metadata)

def load_bm25_index(index_dir: str) -> bm25s.BM25:
    """Load a previously built BM25 index, with its metadata corpus."""
    return bm25s.BM25.load(index_dir, load_corpus=True)


def search_questions(retriever: bm25s.BM25, questions: list[str],
                        k: int) -> list[MinimalSource]:
    """Return the top-k sources for a single question."""
    query_tokens = bm25s.tokenize(questions, stopwords=None, stemmer=None)
    results, scores = retriever.retrieve(query_tokens, k=k, show_progress=True)
    sources = []
    for res in results:
        for doc in res:
            sources.append(MinimalSource(**doc))
    return sources