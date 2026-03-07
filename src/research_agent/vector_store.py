from __future__ import annotations

from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .models import SourceDocument


class SourceIndexer:
    def __init__(self, embedding_model: str) -> None:
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

    def build(self, docs: list[SourceDocument], output_dir: Path) -> None:
        if not docs:
            return

        lc_docs = [
            Document(
                page_content=d.content or d.snippet,
                metadata={"title": d.title, "url": d.url, "type": d.source_type},
            )
            for d in docs
        ]
        db = FAISS.from_documents(lc_docs, self.embeddings)
        output_dir.mkdir(parents=True, exist_ok=True)
        db.save_local(str(output_dir))
