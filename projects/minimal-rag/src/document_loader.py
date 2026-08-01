"""文档读取模块：从 docs 目录加载 Markdown 或文本文件。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Document:
    """表示一份原始文档及其来源路径。"""

    source: str
    text: str


def load_documents(docs_dir: str | Path) -> list[Document]:
    """读取目录下所有 .md 和 .txt 文件，并按文件名排序。"""

    docs_path = Path(docs_dir)

    if not docs_path.is_dir():
        raise NotADirectoryError(f"文档目录不存在: {docs_path}")

    project_root = docs_path.parent
    documents: list[Document] = []

    for path in sorted(docs_path.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue

        text = path.read_text(encoding="utf-8")
        source = path.relative_to(project_root).as_posix()

        documents.append(
            Document(
                source=source,
                text=text,
            )
        )

    return documents