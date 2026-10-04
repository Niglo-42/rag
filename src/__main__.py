import fire
from .parser import parse, open_files, create_chunks
from pathlib import Path
from .retriever import build_bm25_index, load_bm25_index, \
search_questions, fetch_questions, save_answers, build_search_results
import json
from .llm import load_model, build_context, generate_answer


class RagCLI:
    retriever = None
    model = None
    tokenizer = None

    @staticmethod
    def _ensure_retriever() -> None:
        if RagCLI.retriever is None:
            RagCLI.retriever = load_bm25_index("data/processed")

    @staticmethod
    def _ensure_model() -> None:
        if RagCLI.model is None or RagCLI.tokenizer is None:
            RagCLI.tokenizer, RagCLI.model = load_model()

    @staticmethod
    def index(max_chunk_size: int = 2000) -> None:
        py, md, txt = parse()
        try:
            d_py = open_files(py)
            d_md = open_files(md)
            d_txt = open_files(txt)
            all_chunks = create_chunks(d_py, d_md, d_txt, max_chunk_size)
        except OSError as e:
            print(e)
            exit(1)
        build_bm25_index(all_chunks, "data/processed")
        print("Ingestion complete! Indices saved under data/processed/")

    @staticmethod
    def search(query: str, k: int = 5) -> None:
        if k <= 0:
            print(f"k must be a positive integer, got {k}")
            exit(1)
        RagCLI._ensure_retriever()
        min_src = search_questions(RagCLI.retriever, [query], k)[0]
        for src in min_src:
            print(src.file_path)
            print(src.first_character_index, ":", src.last_character_index)
            # print(Path(src.file_path).read_text()[
            #     src.first_character_index:src.last_character_index])

    @staticmethod
    def search_dataset(dataset_path: str, k: int, save_directory: str) -> None:
        if k <= 0:
            print(f"k must be a positive integer, got {k}")
            exit(1)
        try:
            unanswered_questions = fetch_questions(dataset_path)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(e)
            exit(1)
        RagCLI._ensure_retriever()
        questions = [question.question for question in unanswered_questions]
        answers = search_questions(RagCLI.retriever, questions, k)
        lst_min_s_r = build_search_results(unanswered_questions, answers)
        try:
            save_answers(lst_min_s_r, save_directory, k, dataset_path)
        except OSError as e:
            print(e)
            exit(1)

    @staticmethod
    def answer(query: str, k: int) -> None:
        if k <= 0:
            print(f"k must be a positive integer, got {k}")
            exit(1)
        RagCLI._ensure_retriever()
        RagCLI._ensure_model()
        answers = search_questions(RagCLI.retriever, [query], k)[0]
        answer = generate_answer(RagCLI.tokenizer, RagCLI.model, query, answers)
        print(answer)

    @staticmethod
    def answer_dataset(student_search_results_path: str,
                       save_directory: str) -> None:
        if not RagCLI.tokenizer or not RagCLI.model:
            RagCLI.tokenizer, RagCLI.model = load_model()
        

    @staticmethod
    def evaluate(student_search_results_path: str,
                 dataset_path: str, k: int) -> None:
        pass

if __name__ == "__main__":
    try:
        fire.Fire(RagCLI)
    except (EOFError, KeyboardInterrupt):
        print('problema')
    