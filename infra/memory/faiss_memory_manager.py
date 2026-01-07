#####################################################################################
# Simple FAISS-based Memory Manager for Templonix Lite. Direct, synchronous operations - no unnecessary abstractions.
#####################################################################################
import os
import json
import pickle
import logging
import faiss

from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from sentence_transformers import SentenceTransformer

class SimpleFAISSMemory:
    #####################################################################################
    # Initialize the FAISS memory store with embedding model and persistence.
    #####################################################################################
    def __init__(
        self,
        db_path: str = os.getenv("FAISS_DB_PATH"),
        embedding_model: str = os.getenv("LOCAL_EMBEDDING_MODEL"),
        max_results: int = os.getenv("MAX_MEMORY_RESULTS"),
    ):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.max_results = int(max_results) if max_results else 5
        self.logger = logging.getLogger(__name__)

        # Initialize embedding model
        self.logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.metadata = []
        self.documents = []

        # Load existing data if available
        self._load_existing_data()

        self.logger.info(f"SimpleFAISSMemory ready with {len(self.documents)} entries")

    #####################################################################################
    # Load existing FAISS index and metadata from disk.
    #####################################################################################
    def _load_existing_data(self):
        index_path = self.db_path / "faiss_index.bin"
        metadata_path = self.db_path / "metadata.json"
        documents_path = self.db_path / "documents.pkl"

        if not (index_path.exists() and metadata_path.exists() and documents_path.exists()):
            return

        try:
            self.index = faiss.read_index(str(index_path))

            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)

            with open(documents_path, 'rb') as f:
                self.documents = pickle.load(f)

            self.logger.info(f"Loaded {len(self.documents)} existing entries")
        except Exception as e:
            self.logger.warning(f"Failed to load existing data: {e}. Starting fresh.")
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.metadata = []
            self.documents = []

    #####################################################################################
    # Save FAISS index and metadata to disk.
    #####################################################################################
    def _save_data(self):
        try:
            faiss.write_index(self.index, str(self.db_path / "faiss_index.bin"))

            with open(self.db_path / "metadata.json", 'w') as f:
                json.dump(self.metadata, f, indent=2)

            with open(self.db_path / "documents.pkl", 'wb') as f:
                pickle.dump(self.documents, f)

        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")

    #####################################################################################
    # Add a memory or knowledge entry to the store.
    # namespace: "memory" for conversational memories, "knowledge" for documents
    #####################################################################################
    def add_memory(self, content: str, namespace: str = "memory", **kwargs) -> str:
        # Generate embedding
        embedding = self.embedding_model.encode(content)
        embedding = embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(embedding)

        # Add to FAISS index
        self.index.add(embedding)

        # Generate unique ID
        memory_id = f"{namespace}_{len(self.documents)}_{int(datetime.now().timestamp())}"

        # Determine default utility score based on namespace
        default_utility = 0.75 if namespace == "knowledge" else 0.50
        utility_score = kwargs.pop("utility_score", default_utility)

        # Determine tier based on utility score
        if utility_score >= 0.8:
            tier = "Sacred"
        elif utility_score >= 0.3:
            tier = "Active"
        else:
            tier = "Archival"
        tier = kwargs.pop("tier", tier)

        # Store metadata
        metadata = {
            "id": memory_id,
            "namespace": namespace,
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content),
            "utility_score": utility_score,
            "tier": tier,
            "access_count": 0,
            "last_accessed": None,
            **kwargs
        }

        self.metadata.append(metadata)
        self.documents.append(content)

        # Save to disk
        self._save_data()

        self.logger.info(f"Added {namespace} entry {memory_id}")
        return memory_id

    #####################################################################################
    # Search memories/knowledge using semantic similarity.
    # namespace: Filter by namespace, or None to search all.
    #####################################################################################
    def search_memory(
        self,
        query: str,
        namespace: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if len(self.documents) == 0:
            return []

        search_limit = limit or self.max_results

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)

        # Search FAISS index - get more results than needed for filtering
        k = min(search_limit * 3, len(self.documents))
        scores, indices = self.index.search(query_embedding, k)

        # Format and filter results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            entry_namespace = self.metadata[idx].get("namespace", "memory")

            # Filter by namespace if specified
            if namespace is not None and entry_namespace != namespace:
                continue

            # Update access tracking
            self.metadata[idx]["access_count"] = self.metadata[idx].get("access_count", 0) + 1
            self.metadata[idx]["last_accessed"] = datetime.now().isoformat()

            result = {
                "id": self.metadata[idx]["id"],
                "content": self.documents[idx],
                "score": float(score),
                "metadata": self.metadata[idx],
                "namespace": entry_namespace,
                "timestamp": self.metadata[idx]["timestamp"]
            }
            results.append(result)

            if len(results) >= search_limit:
                break

        # Save updated access counts
        if results:
            self._save_data()

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    #####################################################################################
    # Search across ALL namespaces (knowledge + memory) and return unified results.
    # Results are tagged with their source namespace for clear attribution.
    #####################################################################################
    def search_all(
        self,
        query: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if len(self.documents) == 0:
            return []

        search_limit = limit or self.max_results

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)

        # Search FAISS index - no namespace filtering
        k = min(search_limit, len(self.documents))
        scores, indices = self.index.search(query_embedding, k)

        # Format results with namespace attribution
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            entry_namespace = self.metadata[idx].get("namespace", "memory")

            # Update access tracking
            self.metadata[idx]["access_count"] = self.metadata[idx].get("access_count", 0) + 1
            self.metadata[idx]["last_accessed"] = datetime.now().isoformat()

            result = {
                "id": self.metadata[idx]["id"],
                "content": self.documents[idx],
                "score": float(score),
                "metadata": self.metadata[idx],
                "namespace": entry_namespace,
                "timestamp": self.metadata[idx]["timestamp"],
                "source_type": "KNOWLEDGE" if entry_namespace == "knowledge" else "MEMORY"
            }
            results.append(result)

        # Save updated access counts
        if results:
            self._save_data()

        # Sort by score (already sorted by FAISS, but ensure consistency)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    #####################################################################################
    # Get total number of stored entries, optionally filtered by namespace.
    #####################################################################################
    def get_memory_count(self, namespace: Optional[str] = None) -> int:
        if namespace is None:
            return len(self.documents)
        return sum(1 for m in self.metadata if m.get("namespace") == namespace)

    #####################################################################################
    # Get statistics about the memory store.
    #####################################################################################
    def get_stats(self) -> Dict[str, Any]:
        memory_count = self.get_memory_count("memory")
        knowledge_count = self.get_memory_count("knowledge")

        # Count by tier
        tier_counts = {"Sacred": 0, "Active": 0, "Archival": 0}
        for m in self.metadata:
            tier = m.get("tier", "Active")
            if tier in tier_counts:
                tier_counts[tier] += 1

        return {
            "total_entries": len(self.documents),
            "memory_count": memory_count,
            "knowledge_count": knowledge_count,
            "tier_counts": tier_counts,
            "db_path": str(self.db_path)
        }

    #####################################################################################
    # DANGER ZONE: Clear entries by namespace or all entries.
    #####################################################################################
    def clear_memories(self, namespace: Optional[str] = None):
        if namespace is None:
            # Clear everything
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.metadata = []
            self.documents = []
            self._save_data()
            self.logger.info("Cleared all entries")
        else:
            # Clear specific namespace - rebuild index without that namespace
            indices_to_keep = []
            for i, meta in enumerate(self.metadata):
                if meta.get("namespace") != namespace:
                    indices_to_keep.append(i)

            if len(indices_to_keep) == len(self.metadata):
                self.logger.info(f"No entries found for namespace {namespace}")
                return

            # Rebuild index with remaining entries
            new_index = faiss.IndexFlatIP(self.embedding_dim)
            new_metadata = []
            new_documents = []

            for i in indices_to_keep:
                # Re-encode and add to new index
                embedding = self.embedding_model.encode(self.documents[i])
                embedding = embedding.reshape(1, -1).astype('float32')
                faiss.normalize_L2(embedding)
                new_index.add(embedding)
                new_metadata.append(self.metadata[i])
                new_documents.append(self.documents[i])

            self.index = new_index
            self.metadata = new_metadata
            self.documents = new_documents
            self._save_data()
            self.logger.info(f"Cleared entries for namespace {namespace}")
