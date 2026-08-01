"""检索测试入口：显示查询命中的文档来源和内容摘要。"""

import argparse

from src.retriever import retrieve


def main() -> None:
    """读取命令行问题并显示前几个检索结果。"""

    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="需要检索的问题")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    results = retrieve(args.query, top_k=args.top_k)

    for index, result in enumerate(results, start=1):
        print(f"\n[{index}] 综合分: {result['score']:.4f}")
        print(f"向量分: {result['vector_score']:.4f}")
        print(f"标题加分: {result['metadata_bonus']:.4f}")
        print("来源:", result["source_file"])
        print("章节:", result["section_title"])
        print("子章节:", result["subsection_title"])
        print("API 模式:", result["api_mode"])
        print("内容:", result["content"][:300].replace("\n", " "))


if __name__ == "__main__":
    main()