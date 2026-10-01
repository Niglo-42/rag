from pathlib import Path
from tqdm import tqdm
from .models import MinimalSource
BASE = "data/raw/vllm-0.10.1"


class Chunk():
    def __init__(self, min_src: MinimalSource, content: str) -> Chunk:
        self.min_src = min_src
        self.content = content

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

def split_by_size(content: str, start: int, end: int, max_chunk_size: int) -> list[tuple[int, int]]:
    res = []
    while start < end:
        limit = start + max_chunk_size
        if limit >= end:
            res.append((start, end))
            break
        cut = content.rfind('\n\n', start, limit)
        if cut == -1:
            cut = content.rfind('\n', start, limit)
        cut = limit if cut == -1 else cut + 1
        res.append((start, cut))
        start = cut
    return res

def find_python_block_starts(content: str) -> list[int]:
    lines = content.splitlines(keepends=True)
    line_starts = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line)
    limits = []
    paren_depth = 0
    in_decorator_run = False
    for i, line in enumerate(lines):
        if paren_depth > 0:
            paren_depth += line.count("(") + line.count("[") + line.count("{")
            paren_depth -= line.count(")") + line.count("]") + line.count("}")
            continue
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        if line.startswith("@"):
            if not in_decorator_run:
                limits.append(line_starts[i])
                in_decorator_run = True
            paren_depth += line.count("(") - line.count(")")
            continue
        if (line.startswith("def ") or line.startswith("async def ")
            or line.startswith("class ")):
            if not in_decorator_run:
                limits.append(line_starts[i])
            in_decorator_run = False
            paren_depth += line.count("(") - line.count(")")
            continue
        if line.startswith("if __name__"):
            limits.append(line_starts[i])
            in_decorator_run = False
            continue
        in_decorator_run = False
    return limits

def is_heading(stripped_line: str) -> bool:
    hash_count = 0
    while hash_count < len(stripped_line) and stripped_line[hash_count] == "#":
        hash_count += 1
    if hash_count == 0 or hash_count > 6:
        return False
    return hash_count < len(stripped_line) and stripped_line[hash_count] == " "

def find_markdown_block_starts(content: str) -> list[int]:
    block_starts = []
    offset = 0
    in_block = False
    for line in content.splitlines(keepends=True):
        line_stripped = line.strip()
        if line_stripped.startswith("```") or line_stripped.startswith("~~~"):
            in_block = not in_block
        elif not in_block and is_heading(line_stripped):
            block_starts.append(offset)
        offset += len(line)
    return block_starts

def build_blocks(content: str, limits: list[int]) -> list[tuple[int, int]]:
    if len(limits) == 0 or limits[0] != 0:
        limits = [0] + limits
    ends = limits[1:] + [len(content)]
    return list(zip(limits, ends))

def make_chunks_for_one_file(path: Path, content: str,
                             limits: list[int],
                             max_chunk_size: int) -> list[Chunk]:
    chunks = []
    for block_start, block_end in build_blocks(content, limits):
        if block_end - block_start <= max_chunk_size:
            blocks = [(block_start, block_end)]
        else:
            blocks = split_by_size(content, block_start, block_end, max_chunk_size)

        for start, end in blocks:
            text = content[start:end]
            if text.strip() == "":
                continue
            chunks.append(Chunk(
                min_src=MinimalSource(
                file_path=path.as_posix(),
                first_character_index=start,
                last_character_index=end),
                content=text,
            ))
    return chunks


def create_chunks(py: dict[Path, str], md: dict[Path, str],
                  txt: dict[Path, str], max_chunk_size: int) -> list[Chunk]:
    all_chunks = []
    for path, content in py.items():
        limits = find_python_block_starts(content)
        all_chunks += make_chunks_for_one_file(path, content, limits, max_chunk_size)
    for path, content in md.items():
        limits = find_markdown_block_starts(content)
        all_chunks += make_chunks_for_one_file(path, content, limits, max_chunk_size)
    for path, content in txt.items():
        all_chunks += make_chunks_for_one_file(path, content, [], max_chunk_size)
    return all_chunks