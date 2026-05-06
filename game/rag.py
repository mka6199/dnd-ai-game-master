"""RAG (Retrieval-Augmented Generation) using ChromaDB.

Stores DnD lore, monster stats, rules, and player history in a persistent
vector database. The agent retrieves relevant context before generating
narration or NPC dialogue.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


CHROMA_PATH = "chroma_db"
COLLECTION_NAME_OPENAI = "dnd_lore"
COLLECTION_NAME_OLLAMA = "dnd_lore_ollama"  # different vector dims => separate collection


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


class LoreStore:
    """Wrapper around a ChromaDB collection for the campaign world.

    Picks an embedding backend (OpenAI or local Ollama) based on LLM_PROVIDER.
    Each backend writes to its own collection so vector dimensions never clash.
    """

    def __init__(self, persist_dir: str = CHROMA_PATH):
        self.client = chromadb.PersistentClient(path=persist_dir)

        if _get_provider() == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            # Strip the trailing /v1 — Chroma's OllamaEmbeddingFunction wants the root URL.
            ollama_root = base_url.rstrip("/")
            if ollama_root.endswith("/v1"):
                ollama_root = ollama_root[:-3]
            embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
            self.embedder = embedding_functions.OllamaEmbeddingFunction(
                url=f"{ollama_root}/api/embeddings",
                model_name=embed_model,
            )
            collection_name = COLLECTION_NAME_OLLAMA
        else:
            self.embedder = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small",
            )
            collection_name = COLLECTION_NAME_OPENAI

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedder,
        )

    def add_documents(self, docs: list[dict]) -> None:
        """Add a batch of lore documents.

        Each doc: {'id': str, 'text': str, 'category': str, 'title': str}
        """
        if not docs:
            return
        self.collection.add(
            ids=[d["id"] for d in docs],
            documents=[d["text"] for d in docs],
            metadatas=[
                {"category": d.get("category", "general"), "title": d.get("title", "")}
                for d in docs
            ],
        )

    def query(self, text: str, k: int = 3, category_filter: str | None = None) -> list[dict]:
        """Retrieve the top-k most relevant docs for a query."""
        where = {"category": category_filter} if category_filter else None
        result = self.collection.query(
            query_texts=[text],
            n_results=k,
            where=where,
        )
        out = []
        if not result["documents"] or not result["documents"][0]:
            return out
        for doc, meta, distance in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            out.append({
                "title": meta.get("title", ""),
                "category": meta.get("category", ""),
                "text": doc,
                "distance": float(distance),
            })
        return out

    def remember(self, summary: str, tag: str = "history") -> None:
        """Store a memory of past player interactions for future retrieval."""
        import uuid
        self.collection.add(
            ids=[f"mem-{uuid.uuid4().hex[:12]}"],
            documents=[summary],
            metadatas=[{"category": tag, "title": "Player Memory"}],
        )

    def count(self) -> int:
        return self.collection.count()


def seed_from_directory(store: LoreStore, lore_dir: str = "data/lore") -> int:
    """Load all .txt files in lore_dir into the vector store.

    Filename pattern: <category>__<title>.txt (e.g., 'monsters__goblin.txt')
    Returns number of documents added.
    """
    if store.count() > 0:
        return 0  # already seeded

    path = Path(lore_dir)
    if not path.exists():
        return 0

    docs = []
    for txt_file in path.glob("*.txt"):
        stem = txt_file.stem
        if "__" in stem:
            category, title = stem.split("__", 1)
        else:
            category, title = "general", stem
        docs.append({
            "id": f"seed-{stem}",
            "text": txt_file.read_text(encoding="utf-8"),
            "category": category,
            "title": title.replace("_", " ").title(),
        })

    store.add_documents(docs)
    return len(docs)
