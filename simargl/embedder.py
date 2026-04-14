"""Pluggable embedder factory.

Usage:
    emb = get_embedder('bge-small')
    emb = get_embedder('bge-large')
    emb = get_embedder('ollama://nomic-embed-text')
    emb = get_embedder('ollama://nomic-embed-text@localhost:11434')
    emb = get_embedder('openai://localhost:1234/nomic-embed-text')   # LM Studio
    emb = get_embedder('openai://localhost:8080/all-minilm')         # llama.cpp
    vectors = emb.encode(['text1', 'text2'])   # float32, L2-normalized, shape (N, dim)

openai:// means OpenAI-compatible API — works with LM Studio, llama.cpp server,
LiteLLM, Jan, Koboldcpp, or any server that exposes POST /v1/embeddings.
No cloud required.
"""
from __future__ import annotations

import urllib.request
import urllib.error
import json

import sys
import numpy as np
from abc import ABC, abstractmethod

from .config import MODELS, DEFAULT_MODEL


class BaseEmbedder(ABC):
    dim: int

    @abstractmethod
    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Return float32 array of shape (N, dim), L2-normalized."""
        ...

    @staticmethod
    def _normalize(vecs: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return (vecs / norms).astype(np.float32)


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, dim: int):
        from sentence_transformers import SentenceTransformer
        self.dim = dim
        print(f"[simargl] Loading model {model_name} ...", file=sys.stderr, flush=True)
        self._model = SentenceTransformer(model_name)
        print(f"[simargl] Model ready.", file=sys.stderr, flush=True)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        # show_progress_bar only when stderr is a tty — never when running under MCP stdio
        show_bar = len(texts) > 1 and sys.stderr.isatty()
        vecs = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_bar,
        )
        return vecs.astype(np.float32)


class OllamaEmbedder(BaseEmbedder):
    """Calls POST {host}/api/embeddings — works with any Ollama instance.

    model_key formats:
      ollama://nomic-embed-text                  → localhost:11434
      ollama://nomic-embed-text@192.168.1.10     → remote machine port 11434
      ollama://nomic-embed-text@192.168.1.10:9999
    """

    def __init__(self, model_name: str, host: str = "http://localhost:11434"):
        self._model = model_name
        self._host = host.rstrip("/")
        self._url = f"{self._host}/api/embeddings"
        # probe dim with a short text
        self.dim = self._probe_dim()

    def _probe_dim(self) -> int:
        vec = self._embed_one("hello")
        return len(vec)

    def _embed_one(self, text: str) -> list[float]:
        payload = json.dumps({"model": self._model, "prompt": text}).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data["embedding"]

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        # Ollama /api/embeddings is one-at-a-time; batch by sequential calls
        vecs = []
        for text in texts:
            vecs.append(self._embed_one(text))
        arr = np.array(vecs, dtype=np.float32)
        return self._normalize(arr)


class OpenAICompatibleEmbedder(BaseEmbedder):
    """Calls POST {base_url}/v1/embeddings — OpenAI-compatible API.

    Works with: LM Studio, llama.cpp server, LiteLLM, Jan, Koboldcpp,
    or any server that exposes the OpenAI embeddings endpoint locally.

    model_key format:  openai://host:port/model-name
      openai://localhost:1234/nomic-embed-text    → LM Studio
      openai://localhost:8080/all-minilm          → llama.cpp
      openai://localhost:4000/nomic-embed-text    → LiteLLM
    """

    def __init__(self, host: str, model_name: str):
        self._host = host.rstrip("/")
        self._model = model_name
        self._url = f"{self._host}/v1/embeddings"
        self.dim = self._probe_dim()

    def _probe_dim(self) -> int:
        vecs = self._embed_batch(["hello"])
        return len(vecs[0])

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({
            "model": self._model,
            "input": texts,
        }).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Embedding server error {e.code}: {e.read().decode()}") from e
        # OpenAI format: data[].embedding
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        vecs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vecs.extend(self._embed_batch(batch))
        arr = np.array(vecs, dtype=np.float32)
        return self._normalize(arr)


_cache: dict[str, BaseEmbedder] = {}


def get_embedder(model_key: str = DEFAULT_MODEL) -> BaseEmbedder:
    """Factory.

    model_key formats:
      'bge-small'                               → SentenceTransformerEmbedder (local, CPU/GPU)
      'bge-large'                               → SentenceTransformerEmbedder (local, CPU/GPU)
      'ollama://nomic-embed-text'               → OllamaEmbedder (localhost:11434)
      'ollama://nomic-embed-text@host:port'     → OllamaEmbedder (remote)
      'openai://localhost:1234/nomic-embed-text' → OpenAICompatibleEmbedder (LM Studio)
      'openai://localhost:8080/all-minilm'      → OpenAICompatibleEmbedder (llama.cpp)
    """
    if model_key not in _cache:
        if model_key.startswith("ollama://"):
            rest = model_key[len("ollama://"):]
            if "@" in rest:
                model_name, host_part = rest.rsplit("@", 1)
                if "://" not in host_part:
                    host_part = "http://" + host_part
                if ":" not in host_part.split("//", 1)[1]:
                    host_part = host_part + ":11434"
            else:
                model_name = rest
                host_part = "http://localhost:11434"
            _cache[model_key] = OllamaEmbedder(model_name, host=host_part)

        elif model_key.startswith("openai://"):
            rest = model_key[len("openai://"):]
            if "/" in rest:
                host_part, model_name = rest.rsplit("/", 1)
            else:
                raise ValueError(
                    f"openai:// model key must include model name: openai://host:port/model-name\n"
                    f"  e.g. openai://localhost:1234/nomic-embed-text"
                )
            _cache[model_key] = OpenAICompatibleEmbedder(
                host=f"http://{host_part}", model_name=model_name
            )

    if model_key in _cache:
        return _cache[model_key]

    if model_key not in MODELS:
        raise ValueError(
            f"Unknown model key '{model_key}'.\n"
            f"  Known local models: {list(MODELS)}\n"
            f"  Local server: ollama://nomic-embed-text  or  openai://localhost:1234/model-name"
        )

    if model_key not in _cache:
        cfg = MODELS[model_key]
        _cache[model_key] = SentenceTransformerEmbedder(cfg["name"], cfg["dim"])
    return _cache[model_key]
