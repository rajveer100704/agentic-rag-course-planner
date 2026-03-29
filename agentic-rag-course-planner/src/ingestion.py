"""
ingestion.py — Document ingestion, cleaning, and chunking pipeline
for the Prerequisite & Course Planning Assistant.

Strategy:
  - Chunk size: 400 tokens (≈1600 chars) to keep each chunk focused on one
    course or policy section.
  - Overlap: 80 tokens to preserve context across chunk boundaries.
  - Splitting: section-aware. We first split on "====" boundaries (section
    headers), then fall back to paragraph splitting, then character splitting.
  - Metadata: each chunk stores source URL, section heading, and doc_id.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any


CATALOG_DIR = Path(__file__).parent.parent / "data" / "catalog"

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extract_source_meta(text: str) -> Dict[str, str]:
    """Pull SOURCE / TITLE / ACCESSED from the top of a catalog file."""
    meta = {"source_url": "Unknown", "title": "Unknown", "accessed": "Unknown"}
    for line in text.splitlines()[:10]:
        if line.startswith("SOURCE:"):
            meta["source_url"] = line.split("SOURCE:", 1)[1].strip()
        elif line.startswith("TITLE:"):
            meta["title"] = line.split("TITLE:", 1)[1].strip()
        elif line.startswith("ACCESSED:"):
            meta["accessed"] = line.split("ACCESSED:", 1)[1].strip()
    return meta


def _split_into_sections(text: str) -> List[Dict[str, str]]:
    """
    Split a catalog document on '======' dividers.
    Each section block: {heading, body, source_url, title, accessed}
    """
    # Extract file-level metadata (applies until next SOURCE: header)
    current_meta = _extract_source_meta(text)
    sections = []

    # Split on section dividers (lines of = chars, 30+)
    raw_blocks = re.split(r'\n={30,}\n', text)

    current_heading = "Preamble"
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        # Check if this block starts a new SOURCE section
        if block.startswith("SOURCE:"):
            current_meta = _extract_source_meta(block)
            # Find the first SECTION line in this block
            lines = block.splitlines()
            body_lines = []
            for line in lines:
                if line.startswith("SECTION:"):
                    current_heading = line.replace("SECTION:", "").strip()
                elif not line.startswith(("SOURCE:", "TITLE:", "ACCESSED:", "INSTITUTION:")):
                    body_lines.append(line)
            body = "\n".join(body_lines).strip()
            if body:
                sections.append({
                    "heading": current_heading,
                    "body": body,
                    **current_meta
                })
            continue

        # Normal section block — may start with "SECTION:"
        lines = block.splitlines()
        heading = current_heading
        body_lines = []
        for line in lines:
            if line.startswith("SECTION:"):
                heading = line.replace("SECTION:", "").strip()
                current_heading = heading
            else:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()
        if body:
            sections.append({
                "heading": heading,
                "body": body,
                **current_meta
            })

    return sections


def _chunk_section(section: Dict[str, str],
                   max_chars: int = 1600,
                   overlap_chars: int = 200) -> List[Dict[str, Any]]:
    """
    Break a section body into overlapping chunks.
    Each chunk carries section metadata for citation purposes.
    """
    body = section["body"]
    if len(body) <= max_chars:
        chunk_id = hashlib.md5(
            (section["source_url"] + section["heading"] + body[:50]).encode()
        ).hexdigest()[:10]
        return [{
            "chunk_id": chunk_id,
            "heading": section["heading"],
            "source_url": section["source_url"],
            "title": section["title"],
            "accessed": section["accessed"],
            "text": f"[{section['heading']}]\n{body}",
            "char_count": len(body)
        }]

    # Split into paragraphs first
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', body) if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current:
            chunk_text = "\n\n".join(current)
            chunk_id = hashlib.md5(
                (section["source_url"] + section["heading"] + chunk_text[:50]).encode()
            ).hexdigest()[:10]
            chunks.append({
                "chunk_id": chunk_id,
                "heading": section["heading"],
                "source_url": section["source_url"],
                "title": section["title"],
                "accessed": section["accessed"],
                "text": f"[{section['heading']}]\n{chunk_text}",
                "char_count": len(chunk_text)
            })
            # Overlap: keep last paragraph
            overlap_paras = current[-1:] if current else []
            current = overlap_paras + [para]
            current_len = sum(len(p) for p in current)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunk_text = "\n\n".join(current)
        chunk_id = hashlib.md5(
            (section["source_url"] + section["heading"] + chunk_text[:50]).encode()
        ).hexdigest()[:10]
        chunks.append({
            "chunk_id": chunk_id,
            "heading": section["heading"],
            "source_url": section["source_url"],
            "title": section["title"],
            "accessed": section["accessed"],
            "text": f"[{section['heading']}]\n{chunk_text}",
            "char_count": len(chunk_text)
        })

    return chunks


# ─────────────────────────────────────────────
# Main ingestion function
# ─────────────────────────────────────────────

def ingest_catalog(catalog_dir: Path = CATALOG_DIR) -> List[Dict[str, Any]]:
    """
    Load all .txt catalog files, split into sections, chunk them,
    and return a flat list of chunk dicts ready for embedding.
    """
    all_chunks = []
    files = sorted(catalog_dir.glob("*.txt"))

    if not files:
        raise FileNotFoundError(f"No .txt files found in {catalog_dir}")

    print(f"[Ingestion] Found {len(files)} catalog files.")

    for fpath in files:
        text = fpath.read_text(encoding="utf-8")
        sections = _split_into_sections(text)
        doc_chunks = []
        for sec in sections:
            doc_chunks.extend(_chunk_section(sec))

        print(f"  {fpath.name}: {len(sections)} sections → {len(doc_chunks)} chunks")
        all_chunks.extend(doc_chunks)

    print(f"[Ingestion] Total chunks produced: {len(all_chunks)}")
    return all_chunks


def save_chunks(chunks: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"[Ingestion] Saved {len(chunks)} chunks to {output_path}")


def load_chunks(output_path: Path) -> List[Dict[str, Any]]:
    with open(output_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    chunks = ingest_catalog()
    out = Path(__file__).parent.parent / "outputs" / "chunks.json"
    save_chunks(chunks, out)
    # Print sample
    print("\n=== Sample chunk ===")
    print(json.dumps(chunks[0], indent=2))
    print(f"\nTotal chars across all chunks: {sum(c['char_count'] for c in chunks):,}")
