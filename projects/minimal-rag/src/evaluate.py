"""RAG 自动评测：计算检索命中率，并可选验证生成回答的引用格式。"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.chat_client import generate_answer
from src.prompt_builder import build_prompt
from src.retriever import retrieve


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "eval_questions.md"


@dataclass(frozen=True)
class EvaluationCase:
    question: str
    expected_file: str
    expected_section: str


def load_cases(path: Path = DEFAULT_QUESTIONS_PATH) -> list[EvaluationCase]:
    """从 Markdown 表格读取问题和预期来源，保持评测数据便于人工审阅。"""

    cases: list[EvaluationCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "问题" in line or "---" in line:
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) != 2 or " / " not in columns[1]:
            continue
        expected_file, expected_section = columns[1].split(" / ", 1)
        cases.append(EvaluationCase(columns[0].strip("`"), expected_file, expected_section))
    return cases


def source_matches(case: EvaluationCase, result: dict) -> bool:
    """文件必须匹配；章节允许命中主章节或子章节。"""

    sections = " ".join(
        str(result.get(name, ""))
        for name in ("section_title", "subsection_title")
    )
    return case.expected_file in str(result.get("source_file", "")) and case.expected_section in sections


def citation_is_valid(answer: str, source_count: int) -> bool:
    """回答至少包含一个引用，且每个引用编号都指向本次检索来源。"""

    citations = [int(value) for value in re.findall(r"\[来源\s+(\d+)\]", answer)]
    return bool(citations) and all(1 <= value <= source_count for value in citations)


def evaluate(
    cases: list[EvaluationCase],
    *,
    top_k: int = 3,
    generate: bool = False,
    retrieve_fn: Callable[[str, int], list[dict]] = retrieve,
) -> dict[str, float | int]:
    """执行可重复评测；生成评测为可选项，避免默认消耗聊天模型额度。"""

    retrieval_hits = 0
    reciprocal_rank_total = 0.0
    citation_hits = 0
    generated_count = 0

    for case in cases:
        results = retrieve_fn(case.question, top_k)
        matching_rank = next(
            (index for index, result in enumerate(results, start=1) if source_matches(case, result)),
            None,
        )
        if matching_rank:
            retrieval_hits += 1
            reciprocal_rank_total += 1 / matching_rank
        if generate and results:
            answer = generate_answer(build_prompt(case.question, results))
            generated_count += 1
            citation_hits += int(citation_is_valid(answer, len(results)))

    total = len(cases)
    return {
        "cases": total,
        "recall_at_k": retrieval_hits / total if total else 0.0,
        "mrr": reciprocal_rank_total / total if total else 0.0,
        "generated_cases": generated_count,
        "citation_valid_rate": citation_hits / generated_count if generated_count else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评测 Minimal RAG 的检索和引用质量")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--generate", action="store_true", help="同时调用聊天模型验证引用格式")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    args = parser.parse_args()

    metrics = evaluate(load_cases(args.questions), top_k=args.top_k, generate=args.generate)
    for name, value in metrics.items():
        print(f"{name}: {value:.4f}" if isinstance(value, float) else f"{name}: {value}")


if __name__ == "__main__":
    main()
