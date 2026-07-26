"""Small, dependency-free vector memory built on the application's SQL database.

The hashing embedder is deterministic, private, and requires no model download. It
combines word and character features, which makes retrieval tolerant of related
word forms and minor spelling differences while remaining safe as an optional
enhancement to the existing prompt construction.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from db.models import Student, VectorMemory

DIMENSIONS = max(128, int(os.getenv("VECTOR_MEMORY_DIMENSIONS", "384")))
ENABLED = os.getenv("VECTOR_MEMORY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
TOKEN_RE = re.compile(r"[a-z0-9]+")


def _features(text: str) -> list[str]:
    words = TOKEN_RE.findall(text.lower())
    features = list(words)
    features.extend(f"w:{words[i]}_{words[i + 1]}" for i in range(len(words) - 1))
    for word in words:
        padded = f"^{word}$"
        features.extend(f"c:{padded[i:i + 3]}" for i in range(max(0, len(padded) - 2)))
    return features


def embed(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for feature in _features(text):
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, "big")
        index = number % DIMENSIONS
        vector[index] += 1.0 if number & (1 << 63) else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def _chunks(text: str, size: int = 900, overlap: int = 140) -> list[str]:
    clean = re.sub(r"[ \t]+", " ", text).strip()
    if not clean:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|(?<=[.!?])\s+", clean) if part.strip()]
    chunks: list[str] = []
    current = ""
    for part in paragraphs:
        if current and len(current) + len(part) + 1 > size:
            chunks.append(current)
            current = f"{current[-overlap:]} {part}".strip()
        else:
            current = f"{current} {part}".strip()
    if current:
        chunks.append(current)
    return chunks


def index_text(db: Session, student_id: str, text: str, source_type: str, source_id: str | None = None) -> int:
    if not ENABLED or not text.strip():
        return 0
    source_id = source_id or uuid.uuid4().hex
    rows = _chunks(text)
    try:
        db.query(VectorMemory).filter(
            VectorMemory.student_id == student_id,
            VectorMemory.source_type == source_type,
            VectorMemory.source_id == source_id,
        ).delete(synchronize_session=False)
        for content in rows:
            db.add(VectorMemory(
                student_id=student_id,
                source_type=source_type,
                source_id=source_id,
                content=content,
                embedding_json=json.dumps(embed(content), separators=(",", ":")),
            ))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return 0
    return len(rows)


def ensure_student_material_indexed(db: Session, student: Student) -> None:
    """Lazily backfill material uploaded before vector memory was introduced."""
    if not ENABLED:
        return
    for source_type, text in (("syllabus", student.syllabus_text), ("notes", student.notes_text)):
        if not text:
            continue
        try:
            exists = db.query(VectorMemory.id).filter(
                VectorMemory.student_id == student.id,
                VectorMemory.source_type == source_type,
                VectorMemory.source_id == source_type,
            ).first()
        except SQLAlchemyError:
            db.rollback()
            return
        if exists is None:
            index_text(db, student.id, text, source_type, source_id=source_type)


def search(db: Session, student_id: str, query: str, limit: int = 5, source_types: set[str] | None = None) -> list[str]:
    if not ENABLED or not query.strip():
        return []
    query_vector = embed(query)
    rows_query = db.query(VectorMemory).filter(VectorMemory.student_id == student_id)
    if source_types:
        rows_query = rows_query.filter(VectorMemory.source_type.in_(source_types))
    scored: list[tuple[float, str]] = []
    try:
        rows = rows_query.order_by(VectorMemory.created_at.desc()).limit(1500).all()
    except SQLAlchemyError:
        db.rollback()
        return []
    for row in rows:
        try:
            vector = json.loads(row.embedding_json)
            score = sum(left * right for left, right in zip(query_vector, vector))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if score >= 0.08:
            scored.append((score, row.content))
    scored.sort(key=lambda item: item[0], reverse=True)
    seen: set[str] = set()
    results = []
    for _, content in scored:
        marker = content[:160]
        if marker not in seen:
            seen.add(marker)
            results.append(content)
        if len(results) >= limit:
            break
    return results


def format_results(results: list[str], max_chars: int = 6000) -> str:
    text = "\n\n--- relevant memory ---\n\n".join(results)
    return text[:max_chars] or "No relevant long-term memory found."
