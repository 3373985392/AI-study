"""切片持久化模块：将切片保存为 JSONL。"""

import json
from dataclasses import asdict
from pathlib import Path

from src.chunker import Chunk


def save_chunks(chunks: list[Chunk], output_path: str | Path) -> None:
    """将每个切片保存为一行 JSON。"""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(
                json.dumps(
                    asdict(chunk),
                    ensure_ascii=False,
                )
                + "\n"
            )