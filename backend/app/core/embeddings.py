import hashlib
import math
import re

DIM = 256
_SPLIT = re.compile(r"\W+")


def _tokens(text: str) -> list:
    return [t for t in _SPLIT.split(text.lower()) if t]


def _bucket(feature: str):
    h = int.from_bytes(hashlib.md5(feature.encode("utf-8")).digest()[:8], "big")
    return h % DIM, (1.0 if (h >> 20) & 1 else -1.0)


def _embed(text: str) -> list:
    vec = [0.0] * DIM
    toks = _tokens(text)
    feats = list(toks) + [f"{a} {b}" for a, b in zip(toks, toks[1:])]
    for f in feats:
        idx, sign = _bucket(f)
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def embed_texts(texts: list) -> list:
    return [_embed(t) for t in texts]


def cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def chunk_text(text: str, size: int = 200, overlap: int = 40) -> list:
    words = (text or "").split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
        i += step
    return chunks
