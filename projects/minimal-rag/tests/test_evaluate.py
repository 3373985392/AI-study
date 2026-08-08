"""RAG 评测工具的离线测试，不连接 Embedding 或聊天模型。"""

import unittest

from src.evaluate import EvaluationCase, citation_is_valid, evaluate


class EvaluationTests(unittest.TestCase):
    def test_recall_and_mrr_are_computed_from_expected_source_rank(self) -> None:
        cases = [EvaluationCase("问题", "docs/watchers.md", "基本示例")]

        def fake_retrieve(question: str, top_k: int) -> list[dict]:
            self.assertEqual(question, "问题")
            self.assertEqual(top_k, 3)
            return [
                {"source_file": "docs/forms.md", "section_title": "表单", "subsection_title": ""},
                {"source_file": "docs/watchers.md", "section_title": "基本示例", "subsection_title": ""},
            ]

        metrics = evaluate(cases, retrieve_fn=fake_retrieve)
        self.assertEqual(metrics["recall_at_k"], 1.0)
        self.assertEqual(metrics["mrr"], 0.5)

    def test_citation_numbers_must_reference_retrieved_sources(self) -> None:
        self.assertTrue(citation_is_valid("结论 [来源 1]", 2))
        self.assertFalse(citation_is_valid("结论 [来源 3]", 2))
        self.assertFalse(citation_is_valid("没有引用", 2))


if __name__ == "__main__":
    unittest.main()
