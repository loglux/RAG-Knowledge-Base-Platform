"""
Text Chunking Service.

Handles splitting text documents into chunks for embedding and indexing.
Supports multiple chunking strategies.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field

from app.config import settings


logger = logging.getLogger(__name__)


class Chunk(BaseModel):
    """Represents a chunk of text with metadata."""

    content: str = Field(..., description="The text content of the chunk")
    index: int = Field(..., description="Index of this chunk in the document")
    start_char: int = Field(..., description="Starting character position in original document")
    end_char: int = Field(..., description="Ending character position in original document")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    def __len__(self) -> int:
        """Return length of chunk content."""
        return len(self.content)

    @property
    def char_count(self) -> int:
        """Get character count."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: Text to split
            metadata: Optional metadata to attach to all chunks

        Returns:
            List of Chunk objects
        """
        pass


class FixedSizeChunking(ChunkingStrategy):
    """
    Fixed-size chunking strategy with overlap.

    Splits text into chunks of approximately equal size with configurable overlap
    between consecutive chunks. Tries to split on sentence boundaries when possible.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        respect_sentence_boundary: bool = True,
    ):
        """
        Initialize fixed-size chunking strategy.

        Args:
            chunk_size: Maximum chunk size in characters (default: from settings)
            chunk_overlap: Number of overlapping characters between chunks (default: from settings)
            respect_sentence_boundary: Try to split on sentence boundaries (default: True)
        """
        self.chunk_size = chunk_size or settings.MAX_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.respect_sentence_boundary = respect_sentence_boundary

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")

        logger.info(
            f"Initialized FixedSizeChunking: size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, respect_boundaries={self.respect_sentence_boundary}"
        )

    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Split text into fixed-size chunks with overlap.

        Args:
            text: Text to split
            metadata: Optional metadata to attach to all chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Normalize whitespace
        text = self._normalize_text(text)

        if len(text) <= self.chunk_size:
            # Text fits in single chunk
            logger.debug(f"Text fits in single chunk: {len(text)} chars")
            return [
                Chunk(
                    content=text,
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=metadata or {},
                )
            ]

        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is not the last chunk and we should respect boundaries
            if end < len(text) and self.respect_sentence_boundary:
                # Try to find a good breaking point
                end = self._find_break_point(text, start, end)

            # Extract chunk content
            chunk_content = text[start:end].strip()

            if chunk_content:  # Only add non-empty chunks
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        index=chunk_index,
                        start_char=start,
                        end_char=end,
                        metadata=metadata or {},
                    )
                )
                chunk_index += 1

            # Move to next chunk with overlap
            start = end - self.chunk_overlap

            # Ensure we make progress even if overlap is large
            if start <= chunks[-1].start_char if chunks else 0:
                start = end

        logger.info(
            f"Split text of {len(text)} chars into {len(chunks)} chunks "
            f"(avg size: {len(text) // len(chunks) if chunks else 0})"
        )

        return chunks

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text whitespace while preserving line breaks.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Replace multiple spaces/tabs with single space, but preserve newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace 3+ newlines with 2 newlines (preserve paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """
        Find a good breaking point near the target end position.

        Tries to break on sentence boundaries, then paragraph boundaries,
        then word boundaries.

        Args:
            text: Full text
            start: Start position of chunk
            end: Target end position

        Returns:
            Adjusted end position
        """
        # Define search window (look back up to 20% of chunk size)
        search_start = max(start, end - int(self.chunk_size * 0.2))
        search_text = text[search_start:end]

        # Try to find sentence boundary (. ! ? followed by space or newline)
        sentence_pattern = r'[.!?][\s\n]'
        matches = list(re.finditer(sentence_pattern, search_text))
        if matches:
            # Take the last match
            last_match = matches[-1]
            return search_start + last_match.end()

        # Try to find paragraph boundary (double newline)
        if '\n\n' in search_text:
            last_para = search_text.rfind('\n\n')
            if last_para > 0:
                return search_start + last_para + 2

        # Try to find word boundary (space)
        if ' ' in search_text:
            last_space = search_text.rfind(' ')
            if last_space > 0:
                return search_start + last_space + 1

        # Fallback: use target end
        return end


class RecursiveChunking(ChunkingStrategy):
    """
    Recursive chunking strategy using LangChain RecursiveCharacterTextSplitter.

    Splits text recursively by different separators to respect document structure:
    1. Paragraphs (double newlines)
    2. Single newlines
    3. Sentences (periods with space)
    4. Words (spaces)
    5. Characters (fallback)

    This approach is "smart" - it preserves natural text boundaries while
    maintaining target chunk sizes.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """
        Initialize recursive chunking strategy.

        Args:
            chunk_size: Maximum chunk size in characters (default: from settings)
            chunk_overlap: Number of overlapping characters between chunks (default: from settings)
        """
        self.chunk_size = chunk_size or settings.MAX_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")

        self.splitter = None
        self.fallback = None

        # Import here to avoid circular dependencies
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            # Initialize LangChain splitter with hierarchical separators
            self.splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                is_separator_regex=False,
                # Hierarchical separators: paragraph → line → sentence → word → char
                separators=[
                    "\n\n",  # Paragraph boundaries
                    "\n",    # Line boundaries
                    ". ",    # Sentence boundaries
                    " ",     # Word boundaries
                    "",      # Character-level (fallback)
                ],
            )
        except Exception as e:
            # Fallback to fixed-size chunking if langchain splitter fails (e.g., py3.12 ForwardRef issues)
            logger.warning(f"RecursiveChunking unavailable, falling back to FixedSizeChunking: {e}")
            self.fallback = FixedSizeChunking(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                respect_sentence_boundary=True,
            )

        logger.info(
            f"Initialized RecursiveChunking: size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )

    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Split text into chunks using recursive strategy.

        Args:
            text: Text to split
            metadata: Optional metadata to attach to all chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Use LangChain splitter (fallback to fixed-size if it fails)
        if self.splitter is None and self.fallback is not None:
            return self.fallback.split(text, metadata=metadata)

        try:
            langchain_chunks = self.splitter.split_text(text)  # type: ignore[union-attr]
        except Exception as e:
            logger.warning(f"RecursiveChunking failed, falling back to FixedSizeChunking: {e}")
            if self.fallback is not None:
                return self.fallback.split(text, metadata=metadata)
            raise

        if not langchain_chunks:
            logger.warning("No chunks created from text")
            return []

        # Convert LangChain chunks to our Chunk objects
        chunks: List[Chunk] = []
        current_pos = 0

        for idx, chunk_content in enumerate(langchain_chunks):
            # Find chunk position in original text
            start_char = text.find(chunk_content, current_pos)
            if start_char == -1:
                # Fallback if exact match not found (shouldn't happen)
                start_char = current_pos

            end_char = start_char + len(chunk_content)

            chunks.append(
                Chunk(
                    content=chunk_content.strip(),
                    index=idx,
                    start_char=start_char,
                    end_char=end_char,
                    metadata=metadata or {},
                )
            )

            # Move position for next chunk search
            current_pos = start_char + 1

        logger.info(
            f"Split text of {len(text)} chars into {len(chunks)} chunks "
            f"(avg size: {len(text) // len(chunks) if chunks else 0})"
        )

        return chunks


class SemanticChunking(ChunkingStrategy):
    """
    Semantic chunking strategy using embeddings to find semantic boundaries.

    Uses sentence embeddings to detect topic changes, then groups semantically
    related sentences into chunks. Optionally adds contextual descriptions
    (Contextual Embeddings) to improve RAG retrieval quality.

    Algorithm:
    1. Split text into sentences
    2. Embed each sentence
    3. Find semantic boundaries (where similarity drops)
    4. Group sentences into initial chunks
    5. Balance chunks (merge small, split large)
    6. Add contextual descriptions (if enabled)
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,  # Not used in semantic chunking
        boundary_method: str = "adaptive",
        sentence_similarity_threshold: float = 0.30,
        merge_similarity_threshold: float = 0.35,
        min_chunk_size: int = 100,
        use_contextual_embeddings: bool = True,
        embeddings_service=None,
        llm_client=None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
    ):
        """
        Initialize semantic chunking strategy.

        Args:
            chunk_size: Maximum chunk size in characters (default: from settings)
            chunk_overlap: Not used in semantic chunking (for compatibility)
            boundary_method: "fixed" or "adaptive" threshold for boundaries
            sentence_similarity_threshold: Threshold for fixed method (0-1)
            merge_similarity_threshold: Threshold for merging chunks (0-1)
            min_chunk_size: Minimum desired chunk size in characters
            use_contextual_embeddings: Add LLM-generated context to chunks
            embeddings_service: Service for generating embeddings
            llm_client: Anthropic client for contextual embeddings
            llm_model: LLM model for contextual embeddings (from global settings)
            llm_provider: LLM provider (from global settings)
        """
        self.max_chunk_size = chunk_size or settings.MAX_CHUNK_SIZE
        self.boundary_method = boundary_method
        self.sentence_similarity_threshold = sentence_similarity_threshold
        self.merge_similarity_threshold = merge_similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.use_contextual_embeddings = use_contextual_embeddings

        # LLM settings from global config
        self.llm_model = llm_model
        self.llm_provider = llm_provider

        # Services will be injected when needed
        self.embeddings_service = embeddings_service
        self.llm_client = llm_client

        # Import NLTK and configure data path
        try:
            import nltk
            import os

            # Use NLTK data from volume (persists across container restarts)
            nltk_data_dir = '/app/nltk_data'
            if os.path.exists(nltk_data_dir) and nltk_data_dir not in nltk.data.path:
                nltk.data.path.insert(0, nltk_data_dir)

            try:
                nltk.data.find('tokenizers/punkt_tab')
            except LookupError:
                logger.info("Downloading NLTK punkt_tab tokenizer to volume...")
                os.makedirs(nltk_data_dir, exist_ok=True)
                nltk.download('punkt_tab', download_dir=nltk_data_dir, quiet=True)

            self.nltk = nltk
        except ImportError:
            raise ImportError(
                "nltk is required for SemanticChunking. "
                "Install it with: pip install nltk"
            )

        # Import numpy and sklearn
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            self.np = np
            self.cosine_similarity = cosine_similarity
        except ImportError:
            raise ImportError(
                "numpy and scikit-learn are required for SemanticChunking. "
                "Install with: pip install numpy scikit-learn"
            )

        logger.info(
            f"Initialized SemanticChunking: max_size={self.max_chunk_size}, "
            f"min_size={self.min_chunk_size}, method={self.boundary_method}, "
            f"contextual={self.use_contextual_embeddings}"
        )

    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Split text into semantically coherent chunks.

        Args:
            text: Text to split
            metadata: Optional metadata to attach to all chunks

        Returns:
            List of Chunk objects with semantic boundaries
        """
        logger.info(f"[SemanticChunking] split() called with text length: {len(text) if text else 0}")

        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Lazy import to avoid circular dependencies
        logger.info(f"[SemanticChunking] Initializing embeddings service...")
        if self.embeddings_service is None:
            from app.core.embeddings_factory import get_embedding_service
            self.embeddings_service = get_embedding_service()
            logger.info(f"[SemanticChunking] Embeddings service initialized: {type(self.embeddings_service).__name__}")
        else:
            logger.info(f"[SemanticChunking] Using existing embeddings service")

        logger.info(f"[SemanticChunking] Checking LLM client (use_contextual={self.use_contextual_embeddings})...")
        if self.use_contextual_embeddings and self.llm_client is None:
            # Check if LLM model is configured in global settings
            if not self.llm_model:
                logger.warning(
                    "No LLM model configured in global settings. "
                    "Disabling contextual embeddings for semantic chunking."
                )
                self.use_contextual_embeddings = False
            # Only supports Anthropic provider for contextual embeddings (prompt caching)
            elif self.llm_provider and self.llm_provider.lower() != "anthropic":
                logger.warning(
                    f"Contextual embeddings only supported with Anthropic provider. "
                    f"Got: {self.llm_provider}. Disabling contextual embeddings."
                )
                self.use_contextual_embeddings = False
            else:
                import anthropic
                import os
                self.llm_client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
                logger.info(f"[SemanticChunking] Anthropic client initialized for model: {self.llm_model}")

        logger.info(f"[SemanticChunking] Starting semantic chunking of {len(text)} characters")

        # Run sync version - no async needed
        logger.info(f"[SemanticChunking] Calling _split_sync()...")
        result = self._split_sync(text, metadata)
        logger.info(f"[SemanticChunking] _split_sync() completed, got {len(result)} chunks")
        return result

    def _get_embeddings_sync(self, texts: list[str]) -> list[list[float]]:
        """
        Get embeddings synchronously using direct HTTP requests in thread pool.

        Uses ThreadPoolExecutor to avoid blocking the event loop when called
        from async context (FastAPI background tasks).
        """
        import requests
        import json
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.core.embeddings_base import EmbeddingProvider

        # Get provider info from embeddings_service
        provider = self.embeddings_service.provider
        model = self.embeddings_service.model
        dimension = self.embeddings_service.dimension

        def get_single_embedding(text: str) -> list[float]:
            """Helper to get embedding for a single text."""
            try:
                if provider == EmbeddingProvider.OLLAMA:
                    # Direct HTTP request to Ollama
                    response = requests.post(
                        f"{self.embeddings_service.base_url}/api/embeddings",
                        json={"model": model, "prompt": text},
                        timeout=30
                    )
                    response.raise_for_status()
                    embedding = response.json()["embedding"]

                elif provider == EmbeddingProvider.OPENAI:
                    # Direct HTTP request to OpenAI
                    import os
                    response = requests.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                            "Content-Type": "application/json"
                        },
                        json={"input": text, "model": model},
                        timeout=30
                    )
                    response.raise_for_status()
                    embedding = response.json()["data"][0]["embedding"]

                elif provider == EmbeddingProvider.VOYAGE:
                    # Direct HTTP request to Voyage
                    import os
                    response = requests.post(
                        "https://api.voyageai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {os.getenv('VOYAGE_API_KEY')}",
                            "Content-Type": "application/json"
                        },
                        json={"input": text, "model": model},
                        timeout=30
                    )
                    response.raise_for_status()
                    embedding = response.json()["data"][0]["embedding"]

                else:
                    raise ValueError(f"Unknown provider: {provider}")

                return embedding

            except Exception as e:
                logger.error(f"Failed to get embedding from {provider}: {e}")
                # Return zero vector on error
                return [0.0] * dimension

        # Use ThreadPoolExecutor to run HTTP requests in parallel threads
        # This prevents blocking the FastAPI event loop
        embeddings = [None] * len(texts)  # Pre-allocate list with correct size

        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks with their index
            future_to_idx = {
                executor.submit(get_single_embedding, text): idx
                for idx, text in enumerate(texts)
            }

            # Collect results in original order
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                embeddings[idx] = future.result()

        return embeddings

    def _split_sync(self, text: str, metadata: Optional[dict]) -> List[Chunk]:
        """Sync implementation of semantic chunking - no async needed."""
        # Same as _split_async but using sync embeddings

        # Ensure NLTK data path is set (use volume path)
        import os
        nltk_data_path = '/app/nltk_data'
        if os.path.exists(nltk_data_path) and nltk_data_path not in self.nltk.data.path:
            self.nltk.data.path.insert(0, nltk_data_path)

        # Step 1: Split into sentences
        logger.info(f"[SemanticChunking] Step 1: Splitting into sentences...")
        sentences = self._split_sentences(text)
        logger.info(f"[SemanticChunking] Step 1 complete: {len(sentences)} sentences")

        if len(sentences) <= 1:
            return [
                Chunk(
                    content=text.strip(),
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=metadata or {},
                )
            ]

        # Step 2: Embed sentences (SYNC)
        logger.info(f"[SemanticChunking] Step 2: Embedding {len(sentences)} sentences (sync)...")
        sentence_embeddings = self._get_embeddings_sync(sentences)
        logger.info(f"[SemanticChunking] Step 2 complete: got {len(sentence_embeddings)} embeddings")

        # Step 3: Find semantic boundaries
        logger.info(f"[SemanticChunking] Step 3: Finding semantic boundaries...")
        boundaries = self._find_boundaries(sentence_embeddings)
        logger.info(f"[SemanticChunking] Step 3 complete: found {len(boundaries)} boundaries")

        # Step 4: Group sentences into chunks
        logger.info(f"[SemanticChunking] Step 4: Grouping sentences into chunks...")
        initial_chunks = self._group_sentences(sentences, boundaries, text)
        logger.info(f"[SemanticChunking] Step 4 complete: created {len(initial_chunks)} initial chunks")

        # Step 5: Balance chunks
        logger.info(f"[SemanticChunking] Step 5: Balancing chunks...")
        chunk_texts = [chunk["content"] for chunk in initial_chunks]
        chunk_embeddings = self._get_embeddings_sync(chunk_texts)
        logger.info(f"[SemanticChunking] Step 5a: embedded {len(chunk_embeddings)} chunks")

        balanced_chunks = self._balance_chunks(
            initial_chunks, chunk_embeddings, text
        )
        logger.info(f"[SemanticChunking] Step 5 complete: balanced to {len(balanced_chunks)} chunks")

        # Step 6: Skip contextual descriptions for now (requires async LLM calls)
        logger.info(f"[SemanticChunking] Step 6: Skipping contextual embeddings in sync mode")

        # Step 7: Convert to Chunk objects
        logger.info(f"[SemanticChunking] Step 7: Converting to Chunk objects...")
        chunks = self._to_chunk_objects(balanced_chunks, metadata)

        logger.info(
            f"Created {len(chunks)} semantic chunks "
            f"(avg size: {sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0})"
        )

        return chunks

    async def _split_async(self, text: str, metadata: Optional[dict]) -> List[Chunk]:
        """Async implementation of semantic chunking."""
        # Ensure NLTK data path is set (important when running in ThreadPoolExecutor)
        import os
        nltk_data_path = '/app/nltk_data'
        if os.path.exists(nltk_data_path) and nltk_data_path not in self.nltk.data.path:
            self.nltk.data.path.insert(0, nltk_data_path)

        # Step 1: Split into sentences
        logger.info(f"[SemanticChunking] Step 1: Splitting into sentences...")
        sentences = self._split_sentences(text)
        logger.info(f"[SemanticChunking] Step 1 complete: {len(sentences)} sentences")
        if len(sentences) <= 1:
            # Single sentence - return as single chunk
            return [
                Chunk(
                    content=text.strip(),
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=metadata or {},
                )
            ]

        # Step 2: Embed sentences
        logger.info(f"[SemanticChunking] Step 2: Embedding {len(sentences)} sentences...")
        sentence_embeddings = await self._embed_sentences(sentences)
        logger.info(f"[SemanticChunking] Step 2 complete: got {len(sentence_embeddings)} embeddings")

        # Step 3: Find semantic boundaries
        logger.info(f"[SemanticChunking] Step 3: Finding semantic boundaries...")
        boundaries = self._find_boundaries(sentence_embeddings)
        logger.info(f"[SemanticChunking] Step 3 complete: found {len(boundaries)} boundaries")

        # Step 4: Group sentences into chunks
        logger.info(f"[SemanticChunking] Step 4: Grouping sentences into chunks...")
        initial_chunks = self._group_sentences(sentences, boundaries, text)
        logger.info(f"[SemanticChunking] Step 4 complete: created {len(initial_chunks)} initial chunks")

        # Step 5: Balance chunks (merge small, split large)
        logger.info(f"[SemanticChunking] Step 5: Balancing chunks...")
        chunk_embeddings = await self._embed_chunks(initial_chunks)
        logger.info(f"[SemanticChunking] Step 5a: embedded {len(chunk_embeddings)} chunks")
        balanced_chunks = self._balance_chunks(
            initial_chunks, chunk_embeddings, text
        )
        logger.info(f"[SemanticChunking] Step 5 complete: balanced to {len(balanced_chunks)} chunks")

        # Step 6: Add contextual descriptions (if enabled)
        if self.use_contextual_embeddings:
            logger.info(f"[SemanticChunking] Step 6: Adding contextual descriptions for {len(balanced_chunks)} chunks...")
            balanced_chunks = await self._add_contextual_descriptions(
                balanced_chunks, text
            )
            logger.info(f"[SemanticChunking] Step 6 complete: contextual descriptions added")
        else:
            logger.info(f"[SemanticChunking] Step 6: Contextual embeddings disabled, skipping")

        # Step 7: Convert to Chunk objects
        logger.info(f"[SemanticChunking] Step 7: Converting to Chunk objects...")
        chunks = self._to_chunk_objects(balanced_chunks, metadata)

        logger.info(
            f"Created {len(chunks)} semantic chunks "
            f"(avg size: {sum(len(c.content) for c in chunks) // len(chunks) if chunks else 0})"
        )

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK."""
        # Detect language (simple heuristic: check for Cyrillic characters)
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text[:1000])
        language = 'russian' if has_cyrillic else 'english'

        sentences = self.nltk.sent_tokenize(text, language=language)
        logger.debug(f"Split into {len(sentences)} sentences")
        return sentences

    async def _embed_sentences(self, sentences: List[str]) -> List[List[float]]:
        """Generate embeddings for sentences."""
        logger.debug(f"Embedding {len(sentences)} sentences...")
        embeddings = []
        for sent in sentences:
            embedding = await self.embeddings_service.generate_embedding(sent)
            embeddings.append(embedding)
        return embeddings

    def _find_boundaries(self, embeddings: List[List[float]]) -> List[int]:
        """
        Find semantic boundaries between sentences.

        Returns:
            List of indices where boundaries occur (after sentence i)
        """
        if len(embeddings) <= 1:
            return []

        # Calculate similarities
        similarities = []
        for i in range(len(embeddings) - 1):
            emb1 = self.np.array(embeddings[i]).reshape(1, -1)
            emb2 = self.np.array(embeddings[i + 1]).reshape(1, -1)
            sim = self.cosine_similarity(emb1, emb2)[0][0]
            similarities.append(sim)

        # Determine threshold
        if self.boundary_method == "adaptive":
            mean_sim = self.np.mean(similarities)
            std_sim = self.np.std(similarities)
            threshold = mean_sim - 1.0 * std_sim
            logger.debug(
                f"Adaptive threshold: {threshold:.4f} "
                f"(mean={mean_sim:.4f}, std={std_sim:.4f})"
            )
        else:
            threshold = self.sentence_similarity_threshold
            logger.debug(f"Fixed threshold: {threshold:.4f}")

        # Find boundaries
        boundaries = []
        for i, sim in enumerate(similarities):
            if sim < threshold:
                boundaries.append(i + 1)  # Boundary after sentence i

        logger.debug(f"Found {len(boundaries)} semantic boundaries")
        return boundaries

    def _group_sentences(
        self, sentences: List[str], boundaries: List[int], original_text: str
    ) -> List[dict]:
        """Group sentences into initial chunks based on boundaries."""
        chunks = []
        current_chunk = []
        current_start = 0

        for i, sent in enumerate(sentences):
            current_chunk.append(sent)
            if i + 1 in boundaries or i == len(sentences) - 1:
                # Create chunk
                chunk_content = " ".join(current_chunk)
                # Find position in original text (approximate)
                start_pos = original_text.find(sent if i == 0 else current_chunk[0], current_start)
                if start_pos == -1:
                    start_pos = current_start
                end_pos = start_pos + len(chunk_content)

                chunks.append({
                    "content": chunk_content,
                    "start_char": start_pos,
                    "end_char": end_pos,
                })
                current_chunk = []
                current_start = end_pos

        return chunks

    async def _embed_chunks(self, chunks: List[dict]) -> List[List[float]]:
        """Generate embeddings for chunks."""
        logger.debug(f"Embedding {len(chunks)} chunks...")
        embeddings = []
        for chunk in chunks:
            embedding = await self.embeddings_service.generate_embedding(chunk["content"])
            embeddings.append(embedding)
        return embeddings

    def _balance_chunks(
        self, chunks: List[dict], chunk_embeddings: List[List[float]], original_text: str
    ) -> List[dict]:
        """
        Balance chunks by merging small ones (if semantically similar)
        and splitting large ones.
        """
        balanced = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            current_embedding = chunk_embeddings[i]

            # Check if too small and can merge
            if len(current["content"]) < self.min_chunk_size and i + 1 < len(chunks):
                next_embedding = chunk_embeddings[i + 1]
                emb1 = self.np.array(current_embedding).reshape(1, -1)
                emb2 = self.np.array(next_embedding).reshape(1, -1)
                similarity = self.cosine_similarity(emb1, emb2)[0][0]

                if similarity > self.merge_similarity_threshold:
                    # Merge chunks
                    merged_content = current["content"] + " " + chunks[i + 1]["content"]
                    current = {
                        "content": merged_content,
                        "start_char": current["start_char"],
                        "end_char": chunks[i + 1]["end_char"],
                    }
                    # Recalculate embedding (approximation: skip for efficiency)
                    i += 1  # Skip next chunk

            # Check if too large - split at sentence boundaries
            if len(current["content"]) > self.max_chunk_size:
                split_chunks = self._split_large_chunk(current)
                balanced.extend(split_chunks)
            else:
                balanced.append(current)

            i += 1

        return balanced

    def _split_large_chunk(self, chunk: dict) -> List[dict]:
        """Split a large chunk at sentence boundaries."""
        sentences = self.nltk.sent_tokenize(chunk["content"])
        split_chunks = []
        temp_sentences = []
        current_start = chunk["start_char"]

        for sent in sentences:
            temp_content = " ".join(temp_sentences + [sent])
            if len(temp_content) > self.max_chunk_size and temp_sentences:
                # Save current accumulation
                content = " ".join(temp_sentences)
                split_chunks.append({
                    "content": content,
                    "start_char": current_start,
                    "end_char": current_start + len(content),
                })
                current_start += len(content) + 1
                temp_sentences = [sent]
            else:
                temp_sentences.append(sent)

        # Add remaining sentences
        if temp_sentences:
            content = " ".join(temp_sentences)
            split_chunks.append({
                "content": content,
                "start_char": current_start,
                "end_char": current_start + len(content),
            })

        return split_chunks

    async def _add_contextual_descriptions(
        self, chunks: List[dict], original_text: str
    ) -> List[dict]:
        """
        Add contextual descriptions to chunks using Claude.

        Following Anthropic's Contextual Retrieval approach with prompt caching.
        """
        logger.info(f"Adding contextual descriptions to {len(chunks)} chunks...")

        DOCUMENT_CONTEXT_PROMPT = """<document>
{doc_content}
</document>"""

        CHUNK_CONTEXT_PROMPT = """Here is the chunk we want to situate within the whole document
<chunk>
{chunk_content}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Answer only with the succinct context and nothing else."""

        for i, chunk in enumerate(chunks):
            try:
                response = self.llm_client.messages.create(
                    model=self.llm_model,
                    max_tokens=1000,
                    temperature=0.0,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": DOCUMENT_CONTEXT_PROMPT.format(
                                        doc_content=original_text
                                    ),
                                    "cache_control": {"type": "ephemeral"},
                                },
                                {
                                    "type": "text",
                                    "text": CHUNK_CONTEXT_PROMPT.format(
                                        chunk_content=chunk["content"]
                                    ),
                                },
                            ],
                        }
                    ],
                )

                context = response.content[0].text
                chunk["contextual_description"] = context

                # Log cache performance for first and last chunk
                if i == 0 or i == len(chunks) - 1:
                    logger.debug(
                        f"Chunk {i}: cache_read={response.usage.cache_read_input_tokens}, "
                        f"cache_create={response.usage.cache_creation_input_tokens}"
                    )

            except Exception as e:
                logger.warning(f"Failed to generate context for chunk {i}: {e}")
                chunk["contextual_description"] = ""

        return chunks

    def _to_chunk_objects(self, chunks: List[dict], base_metadata: Optional[dict]) -> List[Chunk]:
        """Convert chunk dicts to Chunk objects."""
        chunk_objects = []
        for idx, chunk in enumerate(chunks):
            metadata = base_metadata.copy() if base_metadata else {}

            # Add contextual description to metadata if present
            if "contextual_description" in chunk:
                metadata["contextual_description"] = chunk["contextual_description"]

            chunk_objects.append(
                Chunk(
                    content=chunk["content"],
                    index=idx,
                    start_char=chunk["start_char"],
                    end_char=chunk["end_char"],
                    metadata=metadata,
                )
            )

        return chunk_objects


class ChunkingService:
    """
    Service for managing text chunking operations.

    Provides a unified interface for different chunking strategies.
    """

    def __init__(self, strategy: Optional[ChunkingStrategy] = None):
        """
        Initialize chunking service.

        Args:
            strategy: Chunking strategy to use (default: FixedSizeChunking)
        """
        self.strategy = strategy or FixedSizeChunking()
        logger.info(f"Initialized ChunkingService with strategy: {type(self.strategy).__name__}")

    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Chunk text using the configured strategy.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.debug(f"Chunking text of {len(text)} characters")
        chunks = self.strategy.split(text, metadata)

        # Log statistics
        if chunks:
            avg_size = sum(len(c.content) for c in chunks) / len(chunks)
            logger.info(
                f"Created {len(chunks)} chunks. "
                f"Avg size: {avg_size:.0f} chars, "
                f"Min: {min(len(c.content) for c in chunks)}, "
                f"Max: {max(len(c.content) for c in chunks)}"
            )

        return chunks

    def set_strategy(self, strategy: ChunkingStrategy):
        """
        Change the chunking strategy.

        Args:
            strategy: New chunking strategy to use
        """
        self.strategy = strategy
        logger.info(f"Changed chunking strategy to: {type(strategy).__name__}")


# Default service instance
def get_chunking_service(
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    strategy_name: str = "simple",
    llm_model: Optional[str] = None,
    llm_provider: Optional[str] = None,
) -> ChunkingService:
    """
    Get a chunking service instance with specified strategy.

    Args:
        chunk_size: Optional chunk size override
        chunk_overlap: Optional chunk overlap override
        strategy_name: Chunking strategy ("simple", "smart", "semantic")
        llm_model: Optional LLM model for contextual embeddings (semantic chunking)
        llm_provider: Optional LLM provider (semantic chunking)

    Returns:
        ChunkingService instance

    Raises:
        ValueError: If strategy_name is invalid
    """
    # Import enum here to avoid circular dependency
    from app.models.enums import ChunkingStrategy as ChunkingStrategyEnum

    # Map strategy names to classes
    strategy_map = {
        "simple": FixedSizeChunking,
        ChunkingStrategyEnum.SIMPLE.value: FixedSizeChunking,
        "smart": RecursiveChunking,
        ChunkingStrategyEnum.SMART.value: RecursiveChunking,
        "semantic": SemanticChunking,
        ChunkingStrategyEnum.SEMANTIC.value: SemanticChunking,
        # Legacy support (old enum values from DB)
        "fixed_size": FixedSizeChunking,
        "FIXED_SIZE": FixedSizeChunking,  # Old PostgreSQL enum value
        ChunkingStrategyEnum.FIXED_SIZE.value: FixedSizeChunking,
        "paragraph": RecursiveChunking,
        "PARAGRAPH": RecursiveChunking,  # Old PostgreSQL enum value
        ChunkingStrategyEnum.PARAGRAPH.value: RecursiveChunking,
    }

    strategy_class = strategy_map.get(strategy_name)
    if not strategy_class:
        logger.warning(
            f"Unknown chunking strategy '{strategy_name}', falling back to 'simple'"
        )
        strategy_class = FixedSizeChunking

    # Create strategy instance
    # Pass LLM settings only to SemanticChunking
    if strategy_class == SemanticChunking:
        strategy = strategy_class(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            llm_model=llm_model,
            llm_provider=llm_provider,
        )
    else:
        strategy = strategy_class(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    logger.info(f"Created chunking service with strategy: {strategy_class.__name__}")
    return ChunkingService(strategy=strategy)
