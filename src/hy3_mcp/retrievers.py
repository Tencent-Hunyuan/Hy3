"""A dependency-free BM25 retriever for small knowledge bases.

This is a compact implementation of Okapi BM25, enough to give reasonable
lexical retrieval over hundreds-to-thousands of chunks without pulling in a
vector database or external embedding service.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


# ASCII words kept whole; each CJK character becomes its own token so that
# queries without punctuation still match document phrases.
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u3400-\u9fff\uf900-\ufaff\uff66-\uff9f]", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase tokenizer.

    - ASCII words / numbers are kept as whole tokens.
    - Each CJK (and Kana) character is emitted as an individual token, which
      lets lexical matching work for Chinese text even when the query has no
      punctuation (otherwise ``\\w+`` would collapse a whole sentence into a
      single never-matching token).
    """
    return _TOKEN_RE.findall(text.lower())


@dataclass
class BM25Index:
    """In-memory BM25 index over text documents (chunks)."""

    docs: list[list[str]] = None  # list of token lists per doc
    doc_lengths: list[int] = None
    doc_freqs: dict[str, int] = None
    idf: dict[str, float] = None
    avgdl: float = 0.0
    k1: float = 1.5
    b: float = 0.75

    def __post_init__(self) -> None:
        if self.docs is None:
            self.docs = []
        if self.doc_lengths is None:
            self.doc_lengths = []
        if self.doc_freqs is None:
            self.doc_freqs = {}
        if self.idf is None:
            self.idf = {}

    def add_documents(self, tokenized_docs: list[list[str]]) -> None:
        for tokens in tokenized_docs:
            self.docs.append(tokens)
            self.doc_lengths.append(len(tokens))
            seen = set(tokens)
            for term in seen:
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1
        self.avgdl = (
            sum(self.doc_lengths) / len(self.doc_lengths)
            if self.doc_lengths
            else 0.0
        )
        n = len(self.docs)
        for term, df in self.doc_freqs.items():
            # idf with +1 smoothing to avoid zero for unseen query terms.
            self.idf[term] = math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        """Return ``(doc_index, score)`` pairs sorted by descending score."""
        q_tokens = tokenize(query)
        if not q_tokens or not self.docs:
            return []

        scores: list[float] = [0.0] * len(self.docs)
        for term in q_tokens:
            if term not in self.idf:
                continue
            idf = self.idf[term]
            for i, doc in enumerate(self.docs):
                # count occurrences of term in doc i
                freq = doc.count(term)
                if freq == 0:
                    continue
                denom = freq + self.k1 * (
                    1 - self.b + self.b * self.doc_lengths[i] / (self.avgdl or 1.0)
                )
                scores[i] += idf * (freq * (self.k1 + 1)) / denom

        ranked = sorted(
            ((i, s) for i, s in enumerate(scores) if s > 0.0),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]
