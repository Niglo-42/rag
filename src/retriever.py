import bm25s
from .parser import Chunk
from .models import MinimalSource, UnansweredQuestion, MinimalSearchResults, \
MinimalAnswer, StudentSearchResults, StudentSearchResultsAndAnswer
import json
from pathlib import Path
import re


def expand_identifiers(text: str) -> str:
    """Append split sub-words of snake_case/camelCase identifiers,
    so a question referencing only part of a name can still match."""
    identifiers = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', text)
    extra_words = []
    for identifier in identifiers:
        for part in identifier.split('_'):
            extra_words.extend(re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z]|$)', part))
    return text + " " + " ".join(extra_words)

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

### answer dataset

def fetch_search_results(path: str) -> StudentSearchResults:
    """Load a StudentSearchResults JSON file already written by search_dataset."""
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return StudentSearchResults(**data)

def save_answer_results(answers: list[MinimalAnswer], save_directory: str,
                        k: int, source_path: str) -> None:
    """Write a StudentSearchResultsAndAnswer JSON, named after source_path."""
    var = StudentSearchResultsAndAnswer(search_results=answers, k=k)
    save_dir = Path(save_directory)
    save_dir.mkdir(parents=True, exist_ok=True)
    output_path = save_dir / Path(source_path).name
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(var.model_dump(), file, indent=4)

##### evaluate

def fetch_answered_questions(dataset_path: str) -> dict[str, list[MinimalSource]]:
    """Load an AnsweredQuestions file as {question_id: ground-truth sources}."""
    with open(dataset_path, "r", encoding="utf-8") as file:
        dataset = json.load(file)
    questions = dataset.get("rag_questions")
    if questions is None:
        raise ValueError(f"missing 'rag_questions' key in {dataset_path}")
    truth = {}
    for q in questions:
        question_id = q.get("question_id")
        raw_sources = q.get("sources")
        if raw_sources is None:
            raise ValueError(
                f"question {question_id} has no 'sources' field — "
                f"is {dataset_path} really a ground-truth dataset?")
        truth[question_id] = [MinimalSource(**s) for s in raw_sources]
    return truth


def chunks_overlap(a: MinimalSource, b: MinimalSource) -> bool:
    """True if a and b are in the same file and overlap with IoU >= 0.05."""
    if a.file_path != b.file_path:
        return False
    intersection = max(0, min(a.last_character_index, b.last_character_index)
                       - max(a.first_character_index, b.first_character_index))
    length_a = a.last_character_index - a.first_character_index
    length_b = b.last_character_index - b.first_character_index
    union = length_a + length_b - intersection
    if union <= 0:
        return False
    return (intersection / union) >= 0.05


def recall_at_k(retrieved: list[MinimalSource], truth: list[MinimalSource],
                k: int) -> float:
    """Share of truth's sources found among retrieved's top-k."""
    if len(truth) == 0:
        return 1.0
    top_k = retrieved[:k]
    found = 0
    for true_source in truth:
        if any(chunks_overlap(candidate, true_source) for candidate in top_k):
            found += 1
    return found / len(truth)


def evaluate_search_results(results: StudentSearchResults,
                            truth_by_question: dict[str, list[MinimalSource]],
                            k: int) -> dict[int, float]:
    """Average recall@level over all questions, for level in (1, 3, 5, 10).
    with clamps at levels where each int is a k"""
    levels = [1, 3, 5, 10]
    scores: dict[int, list[float]] = {level: [] for level in levels}
    for result in results.search_results:
        truth = truth_by_question.get(result.question_id)
        if truth is None:
            continue
        for level in levels:
            scores[level].append(
                recall_at_k(result.retrieved_sources, truth, min(level, k)))
    return {level: (sum(values) / len(values) if values else 0.0)
           for level, values in scores.items()}