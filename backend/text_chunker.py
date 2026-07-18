"""
Text chunking - recursive character splitter.

Splits long documents into overlapping chunks suitable for embedding.
A Chunk carries metadata (source document, index, length) used later for
retrieval and source citations.
"""
import logging
import re
from dataclasses import dataclass
from typing import List

import config

logger = logging.getLogger(__name__)

# Separators tried in order, from coarse to fine.
_SEPARATORS = ["\n\n", "\n", "。", "；", "；", ".", "!", "?", ";", " ", ""]


@dataclass
class Chunk:
    text: str
    index: int
    doc_name: str
    chunk_id: str
    length: int = 0  # character count (was the source of a previous bug)

    def __post_init__(self):
        # Ensure length is always derived from the actual text.
        self.length = len(self.text)


def _recursive_split(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into chunks no larger than chunk_size.

    Tries separators from coarse to fine. Any piece that is still longer
    than ``chunk_size`` is split further using STRICTLY FINER separators
    (the final empty string means a hard character split). Because each
    level uses a strictly finer separator, the recursion always makes
    progress and is guaranteed to terminate for any input.
    """
    def _hard_split(t: str) -> List[str]:
        return [t[i : i + chunk_size] for i in range(0, len(t), chunk_size)]

    def _split(t: str, seps) -> List[str]:
        if not seps:
            return _hard_split(t)
        sep = seps[0]
        rest = seps[1:]
        if sep == "":
            return _hard_split(t)
        if sep not in t:
            return _split(t, rest)

        parts = t.split(sep)
        chunks: List[str] = []
        current = ""
        for i, part in enumerate(parts):
            # Re-attach the separator to every piece except the last,
            # to preserve sentence/word meaning.
            piece = part + (sep if i < len(parts) - 1 else "")
            if len(current) + len(piece) <= chunk_size:
                current += piece
            else:
                if current:
                    chunks.append(current)
                if len(piece) > chunk_size:
                    # Progress guaranteed: use strictly finer separators.
                    chunks.extend(_split(piece, rest))
                    current = ""
                else:
                    current = piece
        if current:
            chunks.append(current)
        return [c for c in chunks if c.strip()]

    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    return _split(text, _SEPARATORS)


def _merge_overlap(chunks: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
    """Merge small neighbouring chunks and apply overlap."""
    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size // 4)

    merged: List[str] = []
    buf = ""
    for c in chunks:
        if len(buf) + len(c) <= chunk_size:
            buf += ("\n" if buf else "") + c
        else:
            if buf:
                merged.append(buf)
            buf = c
    if buf:
        merged.append(buf)

    if chunk_overlap <= 0:
        return merged

    # Apply rolling overlap between consecutive chunks.
    out: List[str] = []
    for i, c in enumerate(merged):
        if i == 0:
            out.append(c)
        else:
            prev = merged[i - 1]
            overlap_text = prev[-chunk_overlap:] if len(prev) > chunk_overlap else prev
            out.append(overlap_text + ("\n" if overlap_text else "") + c)
    return out


def chunk_text(
    text: str,
    doc_name: str = "document",
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Chunk]:
    """Split `text` into Chunk objects with metadata."""
    chunk_size = chunk_size or config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    text = text or ""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    raw = _recursive_split(text, chunk_size, chunk_overlap)
    merged = _merge_overlap(raw, chunk_size, chunk_overlap)

    chunks: List[Chunk] = []
    for i, piece in enumerate(merged):
        piece = piece.strip()
        if not piece:
            continue
        chunks.append(
            Chunk(
                text=piece,
                index=i,
                doc_name=doc_name,
                chunk_id=f"{doc_name}::{i}",
            )
        )
    logger.info("Chunked %s into %d chunks", doc_name, len(chunks))
    return chunks
