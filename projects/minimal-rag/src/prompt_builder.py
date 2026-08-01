"""提示词构建模块：将问题和检索资料组合成带引用要求的提示词。"""


def build_prompt(question: str, results: list[dict]) -> str:
    """构造要求模型严格依据资料回答的提示词。"""

    source_blocks: list[str] = []

    for index, result in enumerate(results, start=1):
        metadata = [
            f"文件: {result['source_file']}",
            f"文档: {result['document_title']}",
            f"章节: {result['section_title']}",
        ]

        if result["subsection_title"]:
            metadata.append(
                f"子章节: {result['subsection_title']}"
            )

        if result["api_mode"]:
            metadata.append(f"API 模式: {result['api_mode']}")

        source_blocks.append(
            f"[来源 {index}]\n"
            + "\n".join(metadata)
            + f"\n内容:\n{result['content']}"
        )

    sources = "\n\n".join(source_blocks)

    return f"""你是一个严格依据资料回答问题的助手。

回答规则：
1. 只能使用下方资料中的信息。
2. 每个关键结论后必须使用 [来源 1] 这样的格式引用来源。
3. 如果资料不足以回答，应明确说明“根据现有资料无法确定”。
4. 不要编造资料中没有出现的事实。
5. 回答末尾列出实际使用的文件和章节。

用户问题：
{question}

检索资料：
{sources}

请给出简洁、准确且带来源引用的回答：
"""