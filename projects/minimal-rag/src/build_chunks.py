"""构建脚本：读取、清理、切分并保存全部文档。"""

from src.chunk_resizer import resize_chunks
from src.chunk_store import save_chunks
from src.chunker import split_document
from src.document_cleaner import clean_document
from src.document_loader import load_documents


def main() -> None:
    """构建整个知识库的切片文件。"""

    documents = load_documents("docs")
    all_chunks = []

    for document in documents:
        cleaned = clean_document(document)
        semantic_chunks = split_document(cleaned)
        all_chunks.extend(resize_chunks(semantic_chunks))

    save_chunks(all_chunks, "data/chunks.jsonl")

    print("文档数:", len(documents))
    print("切片数:", len(all_chunks))
    print("输出文件: data/chunks.jsonl")


if __name__ == "__main__":
    main()