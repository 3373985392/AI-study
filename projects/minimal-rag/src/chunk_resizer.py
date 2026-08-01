"""切片长度调整模块：拆分过长内容并保留完整代码块。"""

from dataclasses import replace

from src.chunker import Chunk


def _split_units(text: str) -> list[str]:
    """按段落切分，代码块作为不可拆分单元。"""

    units: list[str] = []
    current: list[str] = []
    in_code_block = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current.append(line)
            continue

        if in_code_block:
            current.append(line)
            continue

        if not stripped:
            if current:
                units.append("\n".join(current).strip())
                current.clear()
            continue

        current.append(line)

    if current:
        units.append("\n".join(current).strip())

    return units


def _tail_units(units: list[str], limit: int) -> list[str]:
    """取不超过限制长度的完整末尾单元，作为重叠内容。"""

    result: list[str] = []
    total = 0

    for unit in reversed(units):
        extra = len(unit) + (1 if result else 0)
        if total + extra > limit:
            break
        result.insert(0, unit)
        total += extra

    return result


def resize_chunks(
    chunks: list[Chunk],
    max_chars: int = 1200,
    overlap_chars: int = 100,
) -> list[Chunk]:
    """拆分过长切片，并保留完整单元作为重叠内容。"""

    resized: list[Chunk] = []

    for chunk in chunks:
        if len(chunk.content) <= max_chars:
            resized.append(chunk)
            continue

        units = _split_units(chunk.content)
        current_units: list[str] = []
        current_length = 0
        part_number = 0

        def emit() -> None:
            nonlocal part_number, current_units, current_length

            if not current_units:
                return

            part_number += 1
            content = "\n\n".join(current_units).strip()
            resized.append(
                replace(
                    chunk,
                    chunk_id=f"{chunk.chunk_id}-part-{part_number:02d}",
                    content=content,
                )
            )

        for unit in units:
            extra = len(unit) + (2 if current_units else 0)

            if current_units and current_length + extra > max_chars:
                previous_units = current_units.copy()
                emit()

                current_units = _tail_units(previous_units, overlap_chars)
                current_length = len("\n\n".join(current_units))

            current_units.append(unit)
            current_length = len("\n\n".join(current_units))

        emit()

    return resized