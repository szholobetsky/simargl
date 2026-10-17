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

from .config import MODELS, DEFAULT_MODEL, OLLAMA_BATCH


class BaseEmbedder(ABC):
    dim: int
    index_flush_size: int = 256  # how many texts to accumulate before flushing in indexer

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
    def __init__(self, model_name: str, dim: int,
                 trust_remote_code: bool = False,
                 batch_size: int = 32,
                 max_seq_length: int | None = None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                f"model '{model_name}' runs locally on torch, which is not installed.\n"
                f"  Install it:      pip install simargl[torch]\n"
                f"  Or use Ollama:   --model ollama://granite-embedding:30m   (no torch needed)") from e
        self.dim = dim
        self._batch_size = batch_size
        print(f"[simargl] Loading model {model_name} ...", file=sys.stderr, flush=True)
        self._model = SentenceTransformer(model_name, trust_remote_code=trust_remote_code)
        if max_seq_length is not None:
            self._model.max_seq_length = max_seq_length
        print(f"[simargl] Model ready (batch_size={batch_size}"
              + (f", max_seq_length={max_seq_length}" if max_seq_length else "")
              + ").", file=sys.stderr, flush=True)

    def encode(self, texts: list[str], batch_size: int | None = None) -> np.ndarray:
        bs = batch_size if batch_size is not None else self._batch_size
        # show_progress_bar only when stderr is a tty — never when running under MCP stdio
        show_bar = len(texts) > 1 and sys.stderr.isatty()
        vecs = self._model.encode(
            texts,
            batch_size=bs,
            normalize_embeddings=True,
            show_progress_bar=show_bar,
        )
        return vecs.astype(np.float32)


class OllamaEmbedder(BaseEmbedder):
    """Calls POST {host}/api/embed — Ollama new batch API (v0.1.26+).

    model_key formats:
      ollama://nomic-embed-text                  → localhost:11434
      ollama://nomic-embed-text@192.168.1.10     → remote machine port 11434
      ollama://nomic-embed-text@192.168.1.10:9999
    """

    # /api/embed takes a list: texts go OLLAMA_BATCH per request instead of one request each
    index_flush_size = OLLAMA_BATCH * 4

    def __init__(self, model_name: str, host: str = "http://localhost:11434"):
        self._model = model_name
        self._host = host.rstrip("/")
        self._url = f"{self._host}/api/embed"
        self.dim = self._probe_dim()

    def _probe_dim(self) -> int:
        return len(self._embed_batch(["hello"])[0])

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self._model, "input": texts}).encode()
        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama error {e.code}: {e.read().decode()}") from e
        return data["embeddings"]

    def encode(self, texts: list[str], batch_size: int = OLLAMA_BATCH) -> np.ndarray:
        vecs = []
        for i in range(0, len(texts), batch_size):
            vecs.extend(self._embed_batch(texts[i : i + batch_size]))
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


def parse_ollama_key(model_key: str) -> tuple[str, str]:
    """'ollama://name[@host[:port]]' -> (model name, http://host:port)."""
    rest = model_key[len("ollama://"):]
    if "@" in rest:
        model_name, host_part = rest.rsplit("@", 1)
        if "://" not in host_part:
            host_part = "http://" + host_part
        if ":" not in host_part.split("//", 1)[1]:
            host_part = host_part + ":11434"
    else:
        model_name, host_part = rest, "http://localhost:11434"
    return model_name, host_part


def ollama_models(host: str = "http://localhost:11434", timeout: float = 3) -> list[str]:
    """Models Ollama has at `host` ([] if it does not answer)."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as resp:
            return [m["name"] for m in json.loads(resp.read()).get("models", [])]
    except Exception:
        return []


def ollama_pull(model_key: str, log=print) -> None:
    """Pull an ollama:// model into Ollama (it downloads the model there, not here)."""
    model_name, host = parse_ollama_key(model_key)
    log(f"[simargl] pulling {model_name} into Ollama at {host} …")
    req = urllib.request.Request(f"{host}/api/pull", data=json.dumps({"model": model_name}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    last = ""
    with urllib.request.urlopen(req, timeout=3600) as resp:
        for line in resp:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("error"):
                raise RuntimeError(f"Ollama: {ev['error']}")
            status = ev.get("status", "")
            if ev.get("total"):
                status += f" {100 * ev.get('completed', 0) // ev['total']}%"
            if status != last:
                log(status)
                last = status


def torch_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("sentence_transformers") is not None


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
            model_name, host_part = parse_ollama_key(model_key)
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
        _cache[model_key] = SentenceTransformerEmbedder(
            cfg["name"], cfg["dim"],
            trust_remote_code=cfg.get("trust_remote_code", False),
            batch_size=cfg.get("batch_size", 32),
            max_seq_length=cfg.get("max_seq_length"),
        )
    return _cache[model_key]
