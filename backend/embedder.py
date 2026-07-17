"""
Embedder - Generate vector embeddings for text chunks.
Uses multilingual ONNX model: paraphrase-multilingual-MiniLM-L12-v2
Supports 50+ languages including Chinese and English.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, List

import numpy as np

logger = logging.getLogger(__name__)

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

MULTILINGUAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_DIM = 384
MAX_SEQ_LEN = 128


class MultilingualONNXEmbedder:
    """
    Multilingual embedder using ONNX Runtime + tokenizers.
    Uses paraphrase-multilingual-MiniLM-L12-v2 which supports
    50+ languages (Chinese, English, Japanese, Korean, etc.).
    No torch/sentence-transformers needed.
    """
    _model = None
    _tokenizer = None

    def __init__(self, model_name: str = MULTILINGUAL_MODEL):
        self.model_name = model_name
        self._ensure_loaded()

    @classmethod
    def _ensure_loaded(cls):
        if cls._model is not None:
            return

        import onnxruntime as ort
        from tokenizers import Tokenizer
        from huggingface_hub import hf_hub_download

        logger.info("Downloading multilingual ONNX model: %s", MULTILINGUAL_MODEL)

        tokenizer_path = hf_hub_download(
            repo_id=MULTILINGUAL_MODEL, filename="tokenizer.json"
        )
        onnx_path = hf_hub_download(
            repo_id=MULTILINGUAL_MODEL, filename="onnx/model.onnx"
        )

        cls._tokenizer = Tokenizer.from_file(tokenizer_path)
        logger.info("Tokenizer loaded from: %s", tokenizer_path)

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        cls._model = ort.InferenceSession(
            onnx_path,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        logger.info("Multilingual ONNX model loaded. Dims=%d, Provider=CPU", MODEL_DIM)

    @property
    def dimension(self) -> int:
        return MODEL_DIM

    def _tokenize(self, texts: List[str]):
        encodings = []
        attention_masks = []
        for text in texts:
            enc = self._tokenizer.encode(text)
            ids = enc.ids[:MAX_SEQ_LEN]
            pad_len = MAX_SEQ_LEN - len(ids)
            input_ids = ids + [0] * pad_len
            attn_mask = [1] * len(ids) + [0] * pad_len
            encodings.append(input_ids)
            attention_masks.append(attn_mask)

        token_type_ids = [[0] * MAX_SEQ_LEN for _ in texts]

        return {
            "input_ids": np.array(encodings, dtype=np.int64),
            "attention_mask": np.array(attention_masks, dtype=np.int64),
            "token_type_ids": np.array(token_type_ids, dtype=np.int64),
        }

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        inputs = self._tokenize(texts)
        outputs = self._model.run(
            None,
            {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"],
                "token_type_ids": inputs["token_type_ids"],
            },
        )

        # ONNX model outputs: [token_embeddings, sentence_embedding]
        if len(outputs) >= 2 and outputs[1].shape[0] == len(texts):
            embeddings = outputs[1]
        else:
            embeddings = self._mean_pool(outputs[0], inputs["attention_mask"])

        embeddings_np = np.array(embeddings)
        norms = np.linalg.norm(embeddings_np, axis=1, keepdims=True)
        embeddings_np = embeddings_np / (norms + 1e-08)
        return embeddings_np.tolist()

    @staticmethod
    def _mean_pool(token_embeddings, attention_mask):
        mask_expanded = np.expand_dims(attention_mask.astype(np.float32), axis=-1)
        mask_expanded = np.broadcast_to(mask_expanded, token_embeddings.shape)
        summed = np.sum(token_embeddings * mask_expanded, axis=1)
        counts = np.clip(
            np.sum(attention_mask, axis=1, keepdims=True), 1e-08, None
        )
        return summed / counts

    def embed_query(self, query: str) -> List[float]:
        return self.embed([query])[0]

    async def embed_async(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, texts)


class MockEmbedder:
    """Mock embedder (hash-based) for testing without any model."""

    def __init__(self, dims: int = 384):
        self.dimension_val = dims
        logger.warning("Using MockEmbedder - search results will be inaccurate!")

    @property
    def dimension(self) -> int:
        return self.dimension_val

    def embed(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            np.random.seed(abs(hash(text)) % 2147483648)
            emb = np.random.randn(self.dimension_val).astype(np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-08)
            results.append(emb.tolist())
        return results

    def embed_query(self, query: str) -> List[float]:
        return self.embed([query])[0]

    async def embed_async(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, texts)


def create_embedder():
    """Factory: try multilingual ONNX, then fallback to mock."""
    try:
        # 1) Try multilingual ONNX (no torch needed, supports Chinese)
        embedder = MultilingualONNXEmbedder()
        logger.info(
            "Using multilingual ONNX embedder (%s, %d dims)",
            MULTILINGUAL_MODEL,
            embedder.dimension,
        )
        return embedder
    except RuntimeError as e:
        logger.info("Multilingual ONNX embedder unavailable: %s", e)
    except Exception as e:
        logger.warning("Multilingual ONNX embedder failed: %s", e)

    logger.warning("No embedding model available, using mock embedder")
    return MockEmbedder()
