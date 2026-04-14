"""Shared utility functions."""
from typing import Any
import numpy as np


def preprocess_text(text: Any) -> str:
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    return str(text).strip()


def combine_fields(row: dict, fields: list[str]) -> str:
    parts = [preprocess_text(row.get(f, "")) for f in fields]
    combined = " ".join(p for p in parts if p)
    return combined or "empty"


def norm_path(path: str) -> str:
    if not path:
        return "unknown"
    return str(path).replace("\\", "/").strip()


def module_from_path(path: str) -> str:
    p = norm_path(path)
    parts = p.split("/")
    return parts[0] if len(parts) > 1 else "root"


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Split text into overlapping word chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks
