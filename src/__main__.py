import fire
from .parser import parse, open_files, create_chunks
from pathlib import Path


class RagCLI:
    def index(py: list[Path],
              md: list[Path],
              txt: list[Path],
              max_chunk_size: int = 2000) -> None:
        try:
            d_py = open_files(py)
            d_md = open_files(md)
            d_txt = open_files(txt)
            create_chunks(d_py, d_md, d_txt, max_chunk_size)
        except OSError as e:
            print(e)


    def search(query: str, k: int = 5) -> None:
        pass

    def search_dataset(dataset_path: str, save_dir: str, k: int) -> None:
        pass
    
    def answer(query: str, k: int) -> None:
        pass
    
    def answer_dataset(student_search_results_path: str,
                       save_directory: str) -> None:
        pass
    
    def evaluate(student_search_results_path: str,
                 dataset_path: str, k: int) -> None:
        pass

if __name__ == "__main__":
    try:
        fire.Fire(RagCLI)
    except (EOFError, KeyboardInterrupt):
        print('problema')
    tup = parse()
    if not all(tup):
        print("miss files")
        raise FileNotFoundError
    RagCLI.index(*tup)
    [print(name, len(x)) for x, name in zip(tup, ("python: ", "md: ", "txt: "))]
    