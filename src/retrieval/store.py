"""
Retrieval Layer — Chunking + ChromaDB vector store with BGE embeddings.
"""
import os
import torch
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer


def chunk_document(text: str, source: str, page_num: int = 0) -> list[dict]:
    """Chunk with overlap. Each chunk retains source provenance metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_text(text)
    return [
        {
            "text": chunk,
            "metadata": {
                "source": source,
                "page": page_num,
                "chunk_index": i,
                "char_start": text.find(chunk)
            }
        }
        for i, chunk in enumerate(chunks)
    ]


class DocumentVectorStore:
    def __init__(self, persist_dir: str = None):
        persist_dir = persist_dir or os.environ.get("VECTORSTORE_DIR", "D:/psl-ai-engineer/vectorstore")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=os.environ.get("CHROMA_COLLECTION", "psl_docs"),
            metadata={"hnsw:space": "cosine"}
        )
        embed_model = os.environ.get("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
        self.embedder = SentenceTransformer(embed_model, device="cuda" if torch.cuda.is_available() else "cpu")

    def add_chunks(self, chunks: list[dict]):
        texts = [c["text"] for c in chunks]
        embeddings = self.embedder.encode(texts, batch_size=32, show_progress_bar=True).tolist()
        ids = [f"{c['metadata']['source']}__p{c['metadata']['page']}__c{c['metadata']['chunk_index']}" for c in chunks]
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in chunks],
            ids=ids
        )

    def retrieve(self, query: str, top_k: int = 8) -> list[dict]:
        q_emb = self.embedder.encode([query]).tolist()
        results = self.collection.query(query_embeddings=q_emb, n_results=top_k)
        return [
            {
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            }
            for i in range(len(results["documents"][0]))
        ]

    def clear(self):
        self.client.delete_collection(self.collection.name)
