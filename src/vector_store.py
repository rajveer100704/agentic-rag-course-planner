"""
vector_store.py — Lightweight TF-IDF vector store with BM25-style retrieval.

In production this would use FAISS + sentence-transformers or OpenAI embeddings.
Here we implement a fully self-contained TF-IDF retriever that:
  - builds an inverted index + TF-IDF matrix from chunks
  - supports cosine-similarity-based top-k retrieval
  - returns chunks with scores and citation metadata
  - is swappable with any real vector store (FAISS/Chroma) by changing
    the VectorStore class interface

This means the system runs 100% offline with zero pip dependencies beyond
Python stdlib + json (math, re, collections are stdlib).
"""

import math
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict


# ─────────────────────────────────────────────
# Tokeniser
# ─────────────────────────────────────────────

_STOP_WORDS = {
    "a","an","the","is","in","it","of","to","and","or","for","with",
    "that","this","at","by","on","from","are","be","as","was","were",
    "its","their","they","we","you","he","she","not","but","can","if",
    "all","any","may","must","will","has","have","had","do","does","did",
    "no","so","than","then","when","where","who","what","how","which"
}

def _tokenise(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    # Keep course codes (e.g. cs101, math120) intact
    return [t for t in tokens if t not in _STOP_WORDS or len(t) <= 2]


def _extract_course_codes(text: str) -> List[str]:
    """Extract course codes like CS 101, MATH 120, DS 301 from text."""
    codes = re.findall(r'\b([A-Z]{2,5})\s*(\d{3})\b', text.upper())
    return [f"{dept}{num}" for dept, num in codes]


# ─────────────────────────────────────────────
# TF-IDF Vector Store
# ─────────────────────────────────────────────

class VectorStore:
    """
    Self-contained TF-IDF vector store.
    Supports add(), search(), and persistence via save/load.
    """

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.idf: Dict[str, float] = {}
        self.tf_vecs: List[Dict[str, float]] = []
        self._built = False

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        self.chunks = chunks
        self._built = False

    def build_index(self) -> None:
        """Compute TF-IDF for all chunks."""
        N = len(self.chunks)
        # DF counts
        df: Dict[str, int] = defaultdict(int)
        all_token_lists = []

        for chunk in self.chunks:
            tokens = _tokenise(chunk["text"])
            # Also boost course codes
            codes = _extract_course_codes(chunk["text"])
            tokens = tokens + codes  # Add codes as tokens for boosting
            all_token_lists.append(tokens)
            for tok in set(tokens):
                df[tok] += 1

        # IDF
        self.idf = {
            tok: math.log((N + 1) / (count + 1)) + 1
            for tok, count in df.items()
        }

        # TF-IDF vectors
        self.tf_vecs = []
        for tokens in all_token_lists:
            freq = Counter(tokens)
            total = sum(freq.values()) or 1
            vec = {
                tok: (freq[tok] / total) * self.idf.get(tok, 0)
                for tok in freq
            }
            self.tf_vecs.append(vec)

        self._built = True
        print(f"[VectorStore] Index built: {N} chunks, {len(self.idf)} unique terms")

    def _cosine(self, query_vec: Dict[str, float], doc_vec: Dict[str, float]) -> float:
        dot = sum(query_vec.get(t, 0) * doc_vec.get(t, 0)
                  for t in set(query_vec) & set(doc_vec))
        norm_q = math.sqrt(sum(v**2 for v in query_vec.values())) or 1e-9
        norm_d = math.sqrt(sum(v**2 for v in doc_vec.values())) or 1e-9
        return dot / (norm_q * norm_d)

    def _query_vec(self, query: str) -> Dict[str, float]:
        tokens = _tokenise(query)
        codes = _extract_course_codes(query)
        tokens = tokens + codes
        freq = Counter(tokens)
        total = sum(freq.values()) or 1
        return {
            tok: (freq[tok] / total) * self.idf.get(tok, 1.0)
            for tok in freq
        }

    def search(self, query: str, k: int = 6,
               score_threshold: float = 0.01) -> List[Dict[str, Any]]:
        """Return top-k chunks for a query, with scores."""
        if not self._built:
            raise RuntimeError("Call build_index() before search()")

        q_vec = self._query_vec(query)
        # Course-code exact-match boosting
        query_codes = set(_extract_course_codes(query))

        scores = []
        for i, (chunk, doc_vec) in enumerate(zip(self.chunks, self.tf_vecs)):
            score = self._cosine(q_vec, doc_vec)
            # Boost chunks that mention the exact course codes in the query
            chunk_codes = set(_extract_course_codes(chunk["text"]))
            overlap = query_codes & chunk_codes
            if overlap:
                boost = 0.1 * len(overlap)
                score += boost
            scores.append((score, i))

        scores.sort(reverse=True)
        results = []
        for score, idx in scores[:k]:
            if score < score_threshold:
                continue
            result = dict(self.chunks[idx])
            result["score"] = round(score, 4)
            results.append(result)
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "chunks": self.chunks,
            "idf": self.idf,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"[VectorStore] Saved index to {path}")

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        vs = cls()
        vs.chunks = data["chunks"]
        vs.idf = data["idf"]
        # Rebuild TF-IDF vectors from chunks
        vs.build_index()
        return vs


# ─────────────────────────────────────────────
# Build / load helpers
# ─────────────────────────────────────────────

def build_store(chunks: List[Dict[str, Any]],
                index_path: Path) -> VectorStore:
    vs = VectorStore()
    vs.add_chunks(chunks)
    vs.build_index()
    vs.save(index_path)
    return vs


def load_store(index_path: Path) -> VectorStore:
    return VectorStore.load(index_path)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from ingestion import ingest_catalog, save_chunks

    chunks = ingest_catalog()
    out_chunks = Path(__file__).parent.parent / "outputs" / "chunks.json"
    save_chunks(chunks, out_chunks)

    store = build_store(chunks, Path(__file__).parent.parent / "outputs" / "vector_index.json")

    # Test search
    results = store.search("prerequisites for CS 310 Database Systems", k=4)
    print("\n=== Search Test ===")
    for r in results:
        print(f"  [{r['score']:.3f}] {r['heading']} | {r['source_url']}")
        print(f"    {r['text'][:120]}...")
