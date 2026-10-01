import fire
from .parser import parse, open_files, create_chunks
from pathlib import Path
from .retriever import build_bm25_index, load_bm25_index, search_questions

class RagCLI:
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
        build_bm25_index(all_chunks, "data/processed")
        retriever = load_bm25_index("data/processed")
        min_src = search_questions(retriever, ["What HTTP endpoint is used to dynamically load a LoRA adapter in vLLM?"], 5)
        for src in min_src:
            print(Path(src.file_path).read_text()[src.first_character_index:src.last_character_index])
            print("---------------")
        print(min_src)

    @staticmethod
    def search(query: str, k: int = 5) -> None:
        pass

    @staticmethod
    def search_dataset(dataset_path: str, save_dir: str, k: int) -> None:
        pass

    @staticmethod
    def answer(query: str, k: int) -> None:
        pass

    @staticmethod
    def answer_dataset(student_search_results_path: str,
                       save_directory: str) -> None:
        pass

    @staticmethod
    def evaluate(student_search_results_path: str,
                 dataset_path: str, k: int) -> None:
        pass

if __name__ == "__main__":
    try:
        fire.Fire(RagCLI)
    except (EOFError, KeyboardInterrupt):
        print('problema')
    