from __future__ import annotations

import os
import re
import uuid
from collections import Counter
from pathlib import Path

from research_agent.config import Settings, load_settings
from research_agent.llm import LLMClient

from .models import DocumentChunk, UserDocument

try:
    from docx import Document as DocxDocument
except ModuleNotFoundError:  # pragma: no cover
    DocxDocument = None

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover
    PdfReader = None


WORD_RE = re.compile(r"[a-zA-Z0-9]{3,}")
UPLOAD_ROOT = Path("data/uploads")


def persist_upload(upload, owner_id: int) -> tuple[str, str]:
    suffix = Path(upload.name).suffix.lower()
    safe_suffix = suffix if suffix else ".bin"
    directory = UPLOAD_ROOT / str(owner_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{safe_suffix}"
    destination = directory / filename
    with destination.open("wb") as handle:
        for chunk in upload.chunks():
            handle.write(chunk)
    return str(destination), suffix.lstrip(".") or "bin"


def process_document(document: UserDocument) -> dict:
    file_type, text = extract_text_from_path(document.storage_path, document.name)
    if len(text.strip()) < 20:
        raise ValueError("The uploaded file does not contain enough readable text to query.")

    chunks = chunk_text(text)
    DocumentChunk.objects.filter(document=document).delete()
    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(document=document, chunk_index=index, content=chunk)
            for index, chunk in enumerate(chunks, start=1)
        ]
    )
    document.file_type = file_type
    document.content = text
    document.status = "processed"
    delete_uploaded_file(document.storage_path)
    document.storage_path = ""
    document.save(update_fields=["file_type", "content", "status", "storage_path", "updated_at"])
    return {"document_id": str(document.id), "chunk_count": len(chunks), "name": document.name}


def extract_text_from_path(storage_path: str, original_name: str) -> tuple[str, str]:
    path = Path(storage_path)
    suffix = path.suffix.lower() or Path(original_name).suffix.lower()
    if not path.exists():
        raise ValueError("The uploaded file could not be found on disk.")

    if suffix in {".txt", ".md", ".csv", ".json"}:
        return suffix.lstrip("."), path.read_text(encoding="utf-8", errors="ignore").strip()

    if suffix == ".pdf":
        if PdfReader is None:
            raise ValueError("PDF support is not installed. Add `pypdf` and try again.")
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
        return "pdf", text.strip()

    if suffix == ".docx":
        if DocxDocument is None:
            raise ValueError("DOCX support is not installed. Add `python-docx` and try again.")
        document = DocxDocument(str(path))
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


def build_hybrid_answer(
    question: str,
    document_result: dict,
    research_summary: str,
    research_sources: list[dict],
    settings: Settings | None = None,
) -> dict:
    fallback = _build_hybrid_fallback(question, document_result, research_summary)
    if settings is None:
        try:
            settings = load_settings(require_api_keys=True)
        except Exception:
            settings = None

    if settings is None:
        return {
            "answer": fallback,
            "citations": document_result.get("citations", []),
            "research_sources": research_sources,
            "mode": "hybrid",
        }

    try:
        client = LLMClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
        )
        prompt = (
            "Create one integrated answer using both uploaded-document evidence and live web research.\n"
            "Keep the answer concise but specific. Do not include inline citation markers.\n\n"
            f"Question: {question}\n\n"
            "Document-grounded answer:\n"
            f"{document_result.get('answer', '')}\n\n"
            "Web research summary:\n"
            f"{research_summary}\n"
        )
        answer = client.generate(
            prompt,
            temperature=0.15,
            system_prompt="You merge internal document evidence with external web research into one grounded answer.",
        )
    except Exception:
        answer = fallback

    return {
        "answer": answer or fallback,
        "citations": document_result.get("citations", []),
        "research_sources": research_sources,
        "mode": "hybrid",
    }


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


def delete_uploaded_file(storage_path: str) -> None:
    if not storage_path:
        return
    try:
        os.remove(storage_path)
    except FileNotFoundError:
        return


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


def _build_hybrid_fallback(question: str, document_result: dict, research_summary: str) -> str:
    document_answer = document_result.get("answer", "").strip()
    pieces = [f"For '{question}', the uploaded documents suggest: {document_answer}"] if document_answer else []
    if research_summary.strip():
        pieces.append(f"Live web research adds: {research_summary.strip()}")
    return "\n\n".join(pieces).strip() or "I could not build a strong hybrid answer from the available inputs."


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]
