from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile

from research_agent.config import load_settings
from research_agent.llm import LLMClient

from .models import DocumentChunk, UserDocument

try:
    from docx import Document as DocxDocument
except ModuleNotFoundError:  # pragma: no cover - dependency is optional until installed.
    DocxDocument = None

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - dependency is optional until installed.
    PdfReader = None


WORD_RE = re.compile(r"[a-zA-Z0-9]{3,}")


def ingest_uploaded_document(upload: UploadedFile, owner_id: int, session_id: str | None = None) -> UserDocument:
    file_type, text = extract_text_from_upload(upload)
    if len(text.strip()) < 20:
        raise ValueError("The uploaded file does not contain enough readable text to query.")

    document = UserDocument.objects.create(
        owner_id=owner_id,
        session_id=session_id,
        name=upload.name[:255],
        file_type=file_type,
        content=text,
        status="processed",
    )

    chunks = chunk_text(text)
    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(document=document, chunk_index=index, content=chunk)
            for index, chunk in enumerate(chunks, start=1)
        ]
    )
    return document


def extract_text_from_upload(upload: UploadedFile) -> tuple[str, str]:
    suffix = Path(upload.name).suffix.lower()
    raw = upload.read()
    upload.seek(0)

    if suffix in {".txt", ".md", ".csv", ".json"}:
        return suffix.lstrip("."), raw.decode("utf-8", errors="ignore").strip()

    if suffix == ".pdf":
        if PdfReader is None:
            raise ValueError("PDF support is not installed. Add `pypdf` and try again.")
        reader = PdfReader(upload)
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
        return "pdf", text.strip()

    if suffix == ".docx":
        if DocxDocument is None:
            raise ValueError("DOCX support is not installed. Add `python-docx` and try again.")
        document = DocxDocument(upload)
        text = "\n".join(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())
        return "docx", text.strip()

    raise ValueError("Unsupported file type. Upload .txt, .md, .csv, .json, .pdf, or .docx.")


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text)
    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n") if paragraph.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + chunk_size, len(paragraph))
            chunks.append(paragraph[start:end].strip())
            if end >= len(paragraph):
                break
            start = max(end - overlap, start + 1)
        current = ""

    if current:
        chunks.append(current)
    return chunks


def answer_document_question(question: str, documents: list[UserDocument]) -> dict:
    ranked = rank_chunks(question, documents)
    if not ranked:
        return {
            "answer": "I could not find enough relevant text in the uploaded documents to answer that confidently.",
            "citations": [],
        }

    top_ranked = ranked[:4]
    prompt_context = []
    citations = []
    seen_docs: set[str] = set()

    for index, item in enumerate(top_ranked, start=1):
        prompt_context.append(
            f"[D{index}] Document: {item['document'].name}\n"
            f"Chunk {item['chunk_index']}\n"
            f"{item['content']}"
        )
        document_id = str(item["document"].id)
        if document_id in seen_docs:
            continue
        seen_docs.add(document_id)
        citations.append(
            {
                "document_id": document_id,
                "name": item["document"].name,
                "file_type": item["document"].file_type,
                "chunk_index": item["chunk_index"],
                "excerpt": item["content"][:280].strip(),
            }
        )

    answer = _generate_grounded_answer(question, prompt_context)
    return {"answer": answer, "citations": citations}


def rank_chunks(question: str, documents: list[UserDocument]) -> list[dict]:
    query_terms = Counter(_tokenize(question))
    if not query_terms:
        return []

    ranked: list[dict] = []
    for document in documents:
        for chunk in document.chunks.all():
            tokens = Counter(_tokenize(chunk.content))
            overlap = sum(min(tokens[token], count) for token, count in query_terms.items())
            if overlap == 0:
                continue
            score = overlap / max(len(query_terms), 1)
            ranked.append(
                {
                    "document": document,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "score": score,
                }
            )

    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def _generate_grounded_answer(question: str, prompt_context: list[str]) -> str:
    fallback = _build_fallback_answer(question, prompt_context)
    try:
        settings = load_settings(require_api_keys=True)
        client = LLMClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
    except Exception:
        return fallback

    context_text = "\n\n".join(prompt_context)
    prompt = (
        "Answer the user's question using only the document excerpts below.\n"
        "Do not invent facts. If the excerpts are insufficient, say so clearly.\n"
        "Do not include citation markers in the answer body.\n\n"
        f"Question: {question}\n\n"
        "Document excerpts:\n"
        f"{context_text}"
    )
    try:
        answer = client.generate(
            prompt,
            temperature=0.1,
            system_prompt="You answer questions grounded strictly in uploaded documents.",
        )
        return answer or fallback
    except Exception:
        return fallback


def _build_fallback_answer(question: str, prompt_context: list[str]) -> str:
    snippets = []
    for excerpt in prompt_context[:3]:
        lines = [line.strip() for line in excerpt.splitlines() if line.strip()]
        if len(lines) >= 3:
            snippets.append(lines[2][:220])

    if not snippets:
        return f"I found uploaded documents related to '{question}', but I do not have enough extracted text to answer cleanly yet."

    joined = " ".join(snippets)
    return f"Based on the uploaded documents, the strongest relevant passages indicate: {joined}"


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]
