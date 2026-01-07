#####################################################################################
# Knowledge Loader for Templonix Lite. Handles document ingestion into the FAISS-based knowledge namespace.
#####################################################################################
import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from .faiss_memory_manager import SimpleFAISSMemory


class KnowledgeLoader:
    """Loads and processes documents from the knowledge folder into the vector store."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
    KNOWLEDGE_NAMESPACE = "knowledge"

    #####################################################################################
    # Initialize the KnowledgeLoader with memory manager and configuration.
    #####################################################################################
    def __init__(
        self,
        memory_manager: SimpleFAISSMemory,
        knowledge_dir: str = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        initial_utility_score: float = 0.75
    ):
        self.memory_manager = memory_manager
        self.knowledge_dir = Path(knowledge_dir or os.getenv("KNOWLEDGE_DIR", "knowledge/"))
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.initial_utility_score = initial_utility_score
        self.logger = logging.getLogger(__name__)

        # Manifest tracks processed files to avoid duplicates
        self.manifest_path = self.knowledge_dir / ".knowledge_manifest.json"
        self.manifest = self._load_manifest()

        # Ensure knowledge directory exists
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    #####################################################################################
    # Load the manifest of previously processed files.
    #####################################################################################
    def _load_manifest(self) -> Dict:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load manifest: {e}")
        return {"processed_files": {}, "version": "1.0"}

    #####################################################################################
    # Save the manifest of processed files.
    #####################################################################################
    def _save_manifest(self):
        try:
            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save manifest: {e}")

    #####################################################################################
    # Calculate MD5 hash of a file for change detection.
    #####################################################################################
    def _get_file_hash(self, file_path: Path) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    #####################################################################################
    # Extract text from a PDF file using pypdf.
    #####################################################################################
    def _parse_pdf(self, file_path: Path) -> str:
        try:
            import pypdf
            text_parts = []
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            self.logger.error("pypdf not installed. Run: pip install pypdf")
            raise
        except Exception as e:
            self.logger.error(f"Error parsing PDF {file_path}: {e}")
            raise

    #####################################################################################
    # Extract text from a DOCX file using python-docx.
    #####################################################################################
    def _parse_docx(self, file_path: Path) -> str:
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs)
        except ImportError:
            self.logger.error("python-docx not installed. Run: pip install python-docx")
            raise
        except Exception as e:
            self.logger.error(f"Error parsing DOCX {file_path}: {e}")
            raise

    #####################################################################################
    # Read text from TXT or MD files.
    #####################################################################################
    def _parse_text(self, file_path: Path) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    #####################################################################################
    # Parse a document based on its file extension.
    #####################################################################################
    def _parse_document(self, file_path: Path) -> Optional[str]:
        ext = file_path.suffix.lower()

        if ext == '.pdf':
            return self._parse_pdf(file_path)
        elif ext == '.docx':
            return self._parse_docx(file_path)
        elif ext in {'.txt', '.md'}:
            return self._parse_text(file_path)
        else:
            self.logger.warning(f"Unsupported file type: {ext}")
            return None

    #####################################################################################
    # Split text into overlapping chunks with intelligent break detection.
    #####################################################################################
    def _chunk_text(self, text: str, source_file: str) -> List[Dict]:
        chunks = []
        text = text.strip()
        if not text:
            return chunks

        start = 0
        text_length = len(text)
        chunk_index = 0

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            # Try to find a natural break point if not at the end
            if end < text_length:
                # Look for paragraph break (double newline)
                break_point = text.rfind('\n\n', start + self.chunk_overlap, end)

                # If no paragraph break, look for single newline
                if break_point == -1 or break_point <= start + self.chunk_overlap:
                    break_point = text.rfind('\n', start + self.chunk_overlap, end)

                # If no newline, look for sentence end
                if break_point == -1 or break_point <= start + self.chunk_overlap:
                    for punct in ['. ', '? ', '! ']:
                        bp = text.rfind(punct, start + self.chunk_overlap, end)
                        if bp > start + self.chunk_overlap:
                            break_point = bp + 1
                            break

                # Use the break point if found
                if break_point > start + self.chunk_overlap:
                    end = break_point

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "content": chunk_text,
                    "source_file": source_file,
                    "chunk_index": chunk_index,
                    "char_start": start,
                    "char_end": end
                })
                chunk_index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap if end < text_length else text_length

        return chunks

    #####################################################################################
    # Find all supported documents in the knowledge directory.
    #####################################################################################
    def discover_documents(self) -> List[Path]:
        documents = []
        for ext in self.SUPPORTED_EXTENSIONS:
            # Root level
            documents.extend(self.knowledge_dir.glob(f"*{ext}"))
            # Subdirectories
            documents.extend(self.knowledge_dir.glob(f"**/*{ext}"))

        # Remove duplicates and sort
        documents = sorted(set(documents))
        return documents

    #####################################################################################
    # Main method to process all documents in the knowledge folder.
    #####################################################################################
    def load_and_process_documents(self, force_reload: bool = False) -> Dict:
        summary = {
            "files_discovered": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "errors": [],
            "processed_files": []
        }

        documents = self.discover_documents()
        summary["files_discovered"] = len(documents)

        self.logger.info(f"Discovered {len(documents)} documents in {self.knowledge_dir}")

        for doc_path in documents:
            try:
                file_hash = self._get_file_hash(doc_path)
                relative_path = str(doc_path.relative_to(self.knowledge_dir))

                # Check if file has already been processed and unchanged
                if not force_reload:
                    if relative_path in self.manifest["processed_files"]:
                        stored_hash = self.manifest["processed_files"][relative_path].get("hash")
                        if stored_hash == file_hash:
                            self.logger.info(f"Skipping unchanged file: {relative_path}")
                            summary["files_skipped"] += 1
                            continue

                # Parse the document
                self.logger.info(f"Processing: {relative_path}")
                text = self._parse_document(doc_path)

                if not text or not text.strip():
                    summary["errors"].append(f"No text extracted: {relative_path}")
                    continue

                # Chunk the text
                chunks = self._chunk_text(text, relative_path)

                if not chunks:
                    summary["errors"].append(f"No chunks created: {relative_path}")
                    continue

                # Store each chunk in the knowledge namespace
                for chunk_data in chunks:
                    self.memory_manager.add_memory(
                        content=chunk_data["content"],
                        namespace=self.KNOWLEDGE_NAMESPACE,
                        source_file=chunk_data["source_file"],
                        chunk_index=chunk_data["chunk_index"],
                        total_chunks=len(chunks),
                        char_start=chunk_data["char_start"],
                        char_end=chunk_data["char_end"],
                        utility_score=self.initial_utility_score,
                        tier="Active"
                    )

                # Update manifest
                self.manifest["processed_files"][relative_path] = {
                    "hash": file_hash,
                    "chunks": len(chunks),
                    "char_count": len(text),
                    "processed_at": datetime.now().isoformat()
                }

                summary["files_processed"] += 1
                summary["chunks_created"] += len(chunks)
                summary["processed_files"].append(relative_path)

                self.logger.info(f"Processed {relative_path}: {len(chunks)} chunks")

            except Exception as e:
                error_msg = f"{doc_path.name}: {str(e)}"
                self.logger.error(f"Error processing {doc_path}: {e}")
                summary["errors"].append(error_msg)

        # Save the updated manifest
        self._save_manifest()

        return summary

    #####################################################################################
    # Get statistics about the current knowledge base.
    #####################################################################################
    def get_knowledge_stats(self) -> Dict:
        processed_files = self.manifest.get("processed_files", {})
        total_chunks = sum(f.get("chunks", 0) for f in processed_files.values())
        total_chars = sum(f.get("char_count", 0) for f in processed_files.values())

        return {
            "knowledge_dir": str(self.knowledge_dir),
            "supported_formats": sorted(self.SUPPORTED_EXTENSIONS),
            "files_processed": len(processed_files),
            "total_chunks": total_chunks,
            "total_characters": total_chars,
            "processed_files": processed_files
        }

    #####################################################################################
    # Clear all knowledge from the vector store and reset manifest.
    #####################################################################################
    def clear_knowledge(self, confirm: bool = False) -> str:
        if not confirm:
            return "Clear cancelled. Set confirm=True to proceed with deletion."

        # Clear from vector store
        self.memory_manager.clear_memories(namespace=self.KNOWLEDGE_NAMESPACE)

        # Reset manifest
        self.manifest = {"processed_files": {}, "version": "1.0"}
        self._save_manifest()

        return "Knowledge base cleared successfully."
