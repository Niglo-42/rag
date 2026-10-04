import bm25s
from .parser import Chunk
from .models import MinimalSource, UnansweredQuestion, MinimalSearchResults,\
StudentSearchResults
import json
from pathlib import Path


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
                        k: int) -> list[list[MinimalSource]]:
    """Return the top-k sources for a single question."""
    query_tokens = bm25s.tokenize(questions, stopwords=None, stemmer=None)
    results, scores = retriever.retrieve(query_tokens, k=k, show_progress=True)
    sources = []
    for res in results:
        src = []
        for doc in res:
            src.append(MinimalSource(**doc))
        sources.append(src)
    return sources

def fetch_questions(dataset_path: str) -> list[UnansweredQuestion]:
    res = []
    with open(dataset_path, "r", encoding="utf-8") as file:
        dataset = json.load(file)
        questions = dataset.get("rag_questions")
        if questions is None:
            raise ValueError(f"missing 'rag_questions' key in {dataset_path}")
        for q in questions:
            res.append(UnansweredQuestion(
                question_id=q.get("question_id"), question=q.get("question")
                ))
    return res

def build_search_results(unanswered_questions: list[UnansweredQuestion],
            answers: list[list[MinimalSource]]) -> list[MinimalSearchResults]:
    res = []
    for q, answer in zip(unanswered_questions, answers):
        res.append(MinimalSearchResults(question_id=q.question_id, question=q.question, retrieved_sources=answer))
    return res

def save_answers(lst_min_s_r: list[MinimalSearchResults],
                 save_directory: str,
                 k: int,
                 dataset_path: str) -> None:
    var = StudentSearchResults(search_results=lst_min_s_r, k=k)
    save_directory = Path(save_directory)
    save_directory.mkdir(parents=True, exist_ok=True)
    output_path = save_directory / Path(dataset_path).name
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(var.model_dump(), file, indent=4)