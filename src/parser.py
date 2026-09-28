from pathlib import Path
from tqdm import tqdm
from .models import MinimalSource
import time

BASE = "data/raw/vllm-0.10.1"

def parse() -> tuple[list[Path], list[Path], list[Path]]:
    return (sorted(Path(BASE).rglob("*.py"), key = lambda p: p.as_posix()),
            sorted(Path(BASE).rglob("*.md"), key = lambda p: p.as_posix()),
            sorted(Path(BASE).rglob("*.txt"), key = lambda p: p.as_posix()))

def read_one_file(path: Path) -> str | None:
    """Read one file and return its text, or None if it cannot be read."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as error:
        print(f"[warning] skipped {path}: {error}")
        return None

def open_files(paths: list[Path]) -> dict[Path, str]:
    """Read all files one by one and return {path: content}."""
    contents: dict[Path, str] = {}
    for path in tqdm(paths, desc="Reading files"):
        text = read_one_file(path)
        if text is not None:
            contents[path] = text
    return contents

def assign(metas: list,
           chunks: list,
           path: str,
           start: int, cut: int, content: str):
    metas.append(MinimalSource(file_path=path,
                               first_character_index=start,
                               last_character_index=cut))
    chunks.append(content)

def create_chunks_txt(txt: dict[Path, str],
                     max_chunk_size: int,
                     separators: list[str]) -> tuple[list[str],
                                             list[MinimalSource]]:
    metas = []
    chunks = []
    for path, content in txt.items():
        if path.name != "SECURITY.md":
            continue
        start = 0
        cut = max_chunk_size
        include = "\n" in separators
        while start < len(content):
            if start + max_chunk_size >= len(content):
                assign(metas, chunks, path.as_posix(), start, len(content), content[start:len(content)])
                start += max_chunk_size
            else:
                limit = start + max_chunk_size
                idx = [content.rfind(separator, start, limit) for separator in separators]
                pos = max(idx) if any(i != -1 for i in idx) else -1
                cut = pos + include if pos != -1 else limit
                assign(metas, chunks, path.as_posix(), start, cut - include, content[start:cut])
                start = cut
        debugg(chunks, metas)
    return (chunks, metas)

def debugg(chunks: list[str], metas: list[MinimalSource]) -> None:
    for met, chunk in zip(metas, chunks):
        print(met.first_character_index, met.last_character_index)
        print(chunk)
        print()

def create_chunks(py: dict[Path, str],
                  md: dict[Path, str],
                  txt: dict[Path, str],
                  max_chunk_size: int) -> None:
    chunk_txt = create_chunks_txt(txt, max_chunk_size, ["\n\n"])
    chunk_txt = create_chunks_txt(md, max_chunk_size, ["#", "##", "###", "####", "#####", "######"])
    # 
    # version python doit etre differente
    # on doit verif que ya un (\n ou \t avant "def" ou "async def" ou "class")
    # aussi il faut verifier les décorateurs au dessus donc while str + "@" on check et on recule starta moins qu'on assume
    # que les décorateur et le @ si eux aussi sont précédés d'un \n ou \t alors c'est un décorateur et on coupe ici point.
    # donc meme regle pour tout le monde