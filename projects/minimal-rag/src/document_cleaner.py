"""文档清理模块：规范标题并保留 API 模式上下文。"""

import re

from src.document_loader import Document


_HEADING_ANCHOR = re.compile(r"\s+\{#[^}]+\}\s*$")
_API_DIV = re.compile(r'<div class="(options-api|composition-api)">')
_CLOSING_DIV = re.compile(r"^\s*</div>\s*$")


def clean_document(document: Document) -> Document:
    """清理单份文档，代码块内部内容保持不变。"""

    cleaned_lines: list[str] = []
    in_code_block = False
    api_wrapper_open = False

    for line in document.text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            cleaned_lines.append(line)
            continue

        if in_code_block:
            cleaned_lines.append(line)
            continue

        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue

        api_match = _API_DIV.fullmatch(stripped)
        if api_match:
            api_wrapper_open = True
            cleaned_lines.append(f"[API 模式: {api_match.group(1)}]")
            continue

        if _CLOSING_DIV.fullmatch(line) and api_wrapper_open:
            api_wrapper_open = False
            cleaned_lines.append("[API 模式结束]")
            continue

        if line.startswith("#"):
            line = _HEADING_ANCHOR.sub("", line)

        cleaned_lines.append(line)

    return Document(
        source=document.source,
        text="\n".join(cleaned_lines).strip() + "\n",
    )