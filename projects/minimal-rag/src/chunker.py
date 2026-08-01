"""文档切分模块：根据 Markdown 标题和 API 模式生成语义切片。"""

import re
from dataclasses import dataclass

from src.document_loader import Document


_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_API_MARKER = re.compile(r"^\[API 模式: (.+)\]$")
_API_END_MARKER = re.compile(r"^\[API 模式结束\]$")


@dataclass(frozen=True)
class Chunk:
    """表示一段可用于后续向量化的文本切片。"""

    chunk_id: str
    source_file: str
    document_title: str
    section_title: str
    subsection_title: str
    api_mode: str
    content: str


def split_document(document: Document) -> list[Chunk]:
    """按标题和 API 模式切分一份清理后的文档。"""

    lines = document.text.splitlines()
    document_title = ""
    section_title = ""
    subsection_title = ""
    api_mode = ""
    content_lines: list[str] = []
    chunks: list[Chunk] = []
    sequence = 0

    def flush() -> None:
        nonlocal sequence

        content = "\n".join(content_lines).strip()
        if not content:
            content_lines.clear()
            return

        sequence += 1
        chunks.append(
            Chunk(
                chunk_id=f"{document.source.replace('/', '-')}-{sequence:03d}",
                source_file=document.source,
                document_title=document_title,
                section_title=section_title,
                subsection_title=subsection_title,
                api_mode=api_mode,
                content=content,
            )
        )
        content_lines.clear()

    for line in lines:
        heading_match = _HEADING.match(line)

        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2)

            if level == 1:
                document_title = title
                continue

            flush()

            if level == 2:
                section_title = title
                subsection_title = ""
                api_mode = ""
            else:
                subsection_title = title

            continue

        api_match = _API_MARKER.match(line.strip())
        if api_match:
            flush()
            api_mode = api_match.group(1)
            continue

        if _API_END_MARKER.match(line.strip()):
            flush()
            api_mode = ""
            continue

        content_lines.append(line)

    flush()
    return chunks