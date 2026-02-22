"""
RAG (Retrieval-Augmented Generation) Service.

Combines retrieval and generation for question answering over knowledge bases.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_base import BaseLLMService, Message
from app.core.llm_factory import create_llm_service
from app.core.retrieval import RetrievalEngine, RetrievedChunk, get_retrieval_engine
from app.models.database import Document as DocumentModel
from app.services.document_analyzer import get_document_analyzer
from app.services.prompts import get_active_chat_prompt, get_active_self_check_prompt
from app.services.query_intent import get_query_intent_extractor

logger = logging.getLogger(__name__)


class RAGResponse(BaseModel):
    """Response from RAG system."""

    answer: str = Field(..., description="Generated answer")
    sources: List[RetrievedChunk] = Field(..., description="Source chunks used")
    query: str = Field(..., description="Original query")
    context_used: str = Field(..., description="Context provided to LLM")
    model: str = Field(..., description="Model used for generation")
    prompt_version_id: Optional[UUID] = Field(default=None, description="Prompt version used")

    @property
    def source_documents(self) -> List[str]:
        """Get unique list of source document IDs."""
        return list(set(chunk.document_id for chunk in self.sources))

    @property
    def confidence_score(self) -> float:
        """
        Get average confidence score from sources.

        Returns average of retrieval scores.
        """
        if not self.sources:
            return 0.0
        return sum(chunk.score for chunk in self.sources) / len(self.sources)


class RAGService:
    """
    Service for Retrieval-Augmented Generation.

    Orchestrates retrieval from vector store and generation with LLM.
    """

    CHAT_USER_TEMPLATE = """<context>
{context}
</context>

<question>{question}{show_question_instructions}</question>

Answer based on the context above:"""

    SELF_CHECK_USER_TEMPLATE = """Question: {question}

Draft Answer: {draft_answer}

Retrieved Context:
{context}"""

    def __init__(
        self,
        retrieval_engine: Optional[RetrievalEngine] = None,
        llm_service: Optional[BaseLLMService] = None,
    ):
        """
        Initialize RAG service.

        Args:
            retrieval_engine: Engine for retrieval
            llm_service: LLM service instance (auto-created if not provided)
        """
        self.retrieval = retrieval_engine or get_retrieval_engine()
        self.llm_service = llm_service or create_llm_service()

        logger.info(f"Initialized RAGService with LLM: {self.llm_service.model}")

    async def query(
        self,
        question: str,
        collection_name: str,
        embedding_model: str,
        top_k: int = 5,
        retrieval_mode: str = "dense",
        lexical_top_k: Optional[int] = None,
        dense_weight: float = 0.6,
        lexical_weight: float = 0.4,
        bm25_match_mode: Optional[str] = None,
        bm25_min_should_match: Optional[int] = None,
        bm25_use_phrase: Optional[bool] = None,
        bm25_analyzer: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_context_chars: Optional[int] = None,
        score_threshold: Optional[float] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_structure: bool = False,
        rerank_enabled: bool = False,
        rerank_provider: Optional[str] = None,
        rerank_model: Optional[str] = None,
        rerank_candidate_pool: Optional[int] = None,
        rerank_top_n: Optional[int] = None,
        rerank_min_score: Optional[float] = None,
        use_mmr: bool = False,
        mmr_diversity: float = 0.5,
        use_self_check: bool = False,
        document_ids: Optional[List[str]] = None,
        context_expansion: Optional[List[str]] = None,
        context_window: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        kb_id: Optional[UUID] = None,
    ) -> RAGResponse:
        """
        Answer a question using RAG.

        Args:
            question: User's question
            collection_name: Qdrant collection to search
            embedding_model: Embedding model used by this KB (for query embedding)
            top_k: Number of chunks to retrieve
            retrieval_mode: Retrieval mode (dense, hybrid)
            lexical_top_k: Lexical top K for BM25 (optional)
            dense_weight: Weight for dense results in hybrid
            lexical_weight: Weight for lexical results in hybrid
            bm25_match_mode: BM25 match mode (strict, balanced, loose)
            bm25_min_should_match: BM25 minimum_should_match percentage (0-100)
            bm25_use_phrase: Include match_phrase clause in BM25 query
            bm25_analyzer: BM25 analyzer profile (auto, mixed, ru, en)
            temperature: LLM temperature (0-2)
            max_tokens: Maximum tokens in response
            llm_model: Override LLM model for this query
            llm_provider: Override LLM provider for this query
            conversation_history: Previous messages for follow-up questions
            use_structure: Use document structure for structured search (default: False)
            rerank_enabled: Enable reranking stage after retrieval
            rerank_provider: Reranking provider hint
            rerank_model: Reranking model hint
            rerank_candidate_pool: Candidate pool size before reranking
            rerank_top_n: Number of chunks to keep after reranking
            rerank_min_score: Optional minimum rerank score threshold
            document_ids: Optional list of document IDs to filter retrieval
            db: Database session for structure lookups (required if use_structure=True)
            kb_id: Knowledge base ID for document lookup (required if use_structure=True)

        Returns:
            RAGResponse with answer and sources

        Raises:
            ValueError: If question is empty or required params missing
            Exception: If RAG process fails
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        mode = retrieval_mode.value if hasattr(retrieval_mode, "value") else str(retrieval_mode)
        logger.info(
            f"RAG query: '{question[:50]}...' "
            f"(collection={collection_name}, mode={mode}, use_structure={use_structure})"
        )

        # Create LLM service with overrides if provided
        llm_service = self.llm_service
        if llm_model or llm_provider:
            logger.info(f"Using custom LLM: {llm_model} ({llm_provider})")
            llm_service = create_llm_service(model=llm_model, provider=llm_provider)

        try:
            # 1. Handle structure-based search if enabled
            chunk_filters = None

            document_filter = None
            if document_ids:
                document_filter = {
                    "document_id": document_ids if len(document_ids) > 1 else document_ids[0]
                }

            logger.debug(
                f"RAG query with use_structure={use_structure}, db={db is not None}, kb_id={kb_id}"
            )

            if use_structure:
                if not db or not kb_id:
                    logger.warning(
                        "use_structure=True but db or kb_id not provided, falling back to semantic search"
                    )
                else:
                    logger.debug("Extracting structure filters...")
                    chunk_filters = await self._extract_structure_filters(
                        question=question, kb_id=kb_id, db=db
                    )
                    if chunk_filters:
                        logger.debug(f"Structure-based search: {chunk_filters}")
                    else:
                        logger.debug("Structure filters returned None, using semantic search")

            if document_filter and chunk_filters and "document_id" in chunk_filters:
                if chunk_filters["document_id"] not in document_ids:
                    logger.warning(
                        "Document filter excludes structured document. Returning empty result."
                    )
                    return RAGResponse(
                        answer="I couldn't find any relevant information in the knowledge base to answer your question.",
                        sources=[],
                        query=question,
                        context_used="",
                        model=llm_service.model,
                    )

            merged_filters = None
            if chunk_filters and document_filter:
                merged_filters = {**document_filter, **chunk_filters}
            elif chunk_filters:
                merged_filters = chunk_filters
            elif document_filter:
                merged_filters = document_filter

            # 2. Retrieve relevant chunks (with optional structure filters)
            if mode == "hybrid":
                if not kb_id:
                    logger.warning("Hybrid retrieval requires kb_id, falling back to dense search")
                    mode = "dense"

            if mode == "hybrid":
                logger.debug(
                    f"Hybrid retrieval (top_k={top_k}, lexical_top_k={lexical_top_k}, mmr={use_mmr})"
                )
                retrieval_result = await self.retrieval.retrieve_hybrid(
                    query=question,
                    collection_name=collection_name,
                    embedding_model=embedding_model,
                    knowledge_base_id=str(kb_id),
                    top_k=top_k,
                    lexical_top_k=lexical_top_k,
                    score_threshold=score_threshold,
                    filters=merged_filters,
                    dense_weight=dense_weight,
                    lexical_weight=lexical_weight,
                    bm25_match_mode=bm25_match_mode,
                    bm25_min_should_match=bm25_min_should_match,
                    bm25_use_phrase=bm25_use_phrase,
                    bm25_analyzer=bm25_analyzer,
                    use_mmr=use_mmr,
                    mmr_diversity=mmr_diversity,
                )
            else:
                logger.debug(
                    f"Retrieving top {top_k} chunks using {embedding_model} (mmr={use_mmr})"
                )
                retrieval_result = await self.retrieval.retrieve(
                    query=question,
                    collection_name=collection_name,
                    embedding_model=embedding_model,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    filters=merged_filters,
                    use_mmr=use_mmr,
                    mmr_diversity=mmr_diversity,
                )

            if not retrieval_result.has_results:
                logger.warning("No relevant chunks found")
                return RAGResponse(
                    answer="I couldn't find any relevant information in the knowledge base to answer your question.",
                    sources=[],
                    query=question,
                    context_used="",
                    model=llm_service.model,
                )

            chunks = retrieval_result.chunks
            if rerank_enabled and chunks:
                provider_normalized = (rerank_provider or "auto").strip().lower()
                if provider_normalized not in {"auto", "voyage", "cohere"}:
                    logger.warning(
                        "Unsupported rerank provider '%s'. Falling back to auto.", rerank_provider
                    )
                    provider_normalized = "auto"
                if provider_normalized == "auto":
                    if settings.VOYAGE_API_KEY:
                        provider_normalized = "voyage"
                    elif settings.COHERE_API_KEY:
                        provider_normalized = "cohere"
                    else:
                        provider_normalized = None
                if provider_normalized == "voyage" and not settings.VOYAGE_API_KEY:
                    logger.warning("Rerank provider 'voyage' selected but VOYAGE_API_KEY is missing")
                    provider_normalized = None
                if provider_normalized == "cohere" and not settings.COHERE_API_KEY:
                    logger.warning("Rerank provider 'cohere' selected but COHERE_API_KEY is missing")
                    provider_normalized = None

                candidate_pool = rerank_candidate_pool or len(chunks)
                candidate_pool = max(1, min(candidate_pool, len(chunks)))
                reranked = await self.retrieval.rerank_results(
                    query=question,
                    chunks=chunks[:candidate_pool],
                    provider=provider_normalized,
                    model=rerank_model,
                    min_score=rerank_min_score,
                )
                keep_n = rerank_top_n or top_k
                keep_n = max(1, keep_n)
                chunks = reranked[:keep_n]

            expansion_modes = context_expansion or []
            window_size = context_window or 0
            if "window" in expansion_modes and window_size > 0:
                chunks = await self.retrieval.expand_windowed(
                    collection_name=collection_name,
                    chunks=chunks,
                    window_size=window_size,
                )

            # 3. Generate answer with context
            context = self.retrieval._assemble_context(chunks)
            if max_context_chars is not None:
                context = self.retrieval._assemble_context(
                    chunks,
                    max_length=max_context_chars,
                )
            elif chunk_filters:
                # For structured question retrieval, avoid truncating the target section.
                context = self.retrieval._assemble_context(
                    chunks,
                    max_length=max_context_chars,
                )
            logger.debug(f"Generating answer with {len(chunks)} chunks")
            # Generate draft answer
            draft_answer, prompt_version_id = await self._generate_answer(
                question=question,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
                llm_service=llm_service,
                conversation_history=conversation_history,
                db=db,
            )

            # Validate and refine answer with self-check (if enabled)
            if use_self_check:
                logger.info("[SELF-CHECK] Running validation on draft answer")
                logger.info("🔍 Running self-check validation on draft answer")
                answer = await self._self_check_answer(
                    question=question,
                    draft_answer=draft_answer,
                    context=context,
                    llm_service=llm_service,
                    db=db,
                )
            else:
                logger.info("[SELF-CHECK] Self-check disabled, using draft answer")
                answer = draft_answer

            logger.info(
                f"RAG completed: {len(answer)} chars answer from {len(retrieval_result.chunks)} sources"
            )

            return RAGResponse(
                answer=answer,
                sources=chunks,
                query=question,
                context_used=context,
                model=llm_service.model,
                prompt_version_id=prompt_version_id,
            )

        except Exception:
            logger.exception("RAG query failed")
            raise

    async def query_document(
        self,
        question: str,
        collection_name: str,
        embedding_model: str,
        document_id: UUID,
        top_k: int = 5,
        db: Optional[AsyncSession] = None,
    ) -> RAGResponse:
        """
        Answer a question using only a specific document.

        Args:
            question: User's question
            collection_name: Collection name
            embedding_model: Embedding model used by this KB (for query embedding)
            document_id: Specific document to query
            top_k: Number of chunks to retrieve

        Returns:
            RAGResponse with answer and sources
        """
        logger.info(f"RAG query on document {document_id}")

        try:
            # Retrieve from specific document
            retrieval_result = await self.retrieval.retrieve_by_document(
                query=question,
                collection_name=collection_name,
                embedding_model=embedding_model,
                document_id=document_id,
                top_k=top_k,
            )

            if not retrieval_result.has_results:
                return RAGResponse(
                    answer="I couldn't find relevant information in this document to answer your question.",
                    sources=[],
                    query=question,
                    context_used="",
                    model=self.llm_service.model,
                )

            # Generate answer
            answer, prompt_version_id = await self._generate_answer(
                question=question,
                context=retrieval_result.context,
                llm_service=self.llm_service,
                db=db,
            )

            return RAGResponse(
                answer=answer,
                sources=retrieval_result.chunks,
                query=question,
                context_used=retrieval_result.context,
                model=self.llm_service.model,
                prompt_version_id=prompt_version_id,
            )

        except Exception as e:
            logger.error(f"RAG document query failed: {e}")
            raise

    async def _generate_answer(
        self,
        question: str,
        context: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        llm_service: Optional[BaseLLMService] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        db: Optional[AsyncSession] = None,
    ) -> tuple[str, Optional[UUID]]:
        """
        Generate answer using LLM with context.

        Args:
            question: User's question
            context: Retrieved context
            temperature: LLM temperature
            max_tokens: Maximum tokens
            llm_service: LLM service to use (defaults to self.llm_service)
            conversation_history: Previous messages for follow-up

        Returns:
            Tuple of (answer text, prompt_version_id)

        Raises:
            Exception: If generation fails
        """
        service = llm_service or self.llm_service

        try:
            # Build messages list starting with system prompt
            system_content = None
            prompt_version_id = None
            if db is not None:
                system_content, prompt_version_id = await get_active_chat_prompt(db)
            if not system_content:
                raise RuntimeError("Active prompt templates are not configured")
            messages = [Message(role="system", content=system_content)]

            # Add conversation history (limit to last 10 messages to avoid token limits)
            if conversation_history:
                recent_history = conversation_history[-10:]
                for msg in recent_history:
                    messages.append(Message(role=msg["role"], content=msg["content"]))

            # Detect "show me question N" style requests to return verbatim text
            show_question_match = re.search(
                r"\b(show|display|give|list)\b.*\bquestion\s+\d+\b",
                question,
                re.IGNORECASE,
            )
            show_question_request = show_question_match is not None

            # Build user prompt with RAG context for current question
            show_question_instructions = ""
            if show_question_request:
                logger.warning(
                    "[DEBUG] show_question context length=%s preview=%r",
                    len(context),
                    context[:2000],
                )
                show_question_instructions = (
                    "\nInstruction: The user is asking to see the question text. "
                    "Return the full, verbatim question from the context, including all subparts "
                    "(a), (b), (c), etc. Do not summarize or add commentary. "
                    "If any subpart is missing from the context, say which parts are missing."
                )

            user_prompt = self.CHAT_USER_TEMPLATE.format(
                context=context,
                question=question,
                show_question_instructions=show_question_instructions,
            )

            # Add current question
            messages.append(Message(role="user", content=user_prompt))

            response = await service.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or settings.OPENAI_MAX_TOKENS,
            )

            answer = response.content.strip()

            logger.debug(
                f"Generated answer: {len(answer)} chars "
                f"(tokens: {response.total_tokens if response.total_tokens else 'N/A'})"
            )

            return answer, prompt_version_id

        except Exception:
            logger.exception("Answer generation failed")
            raise

    async def _self_check_answer(
        self,
        question: str,
        draft_answer: str,
        context: str,
        llm_service: Optional[BaseLLMService] = None,
        db: Optional[AsyncSession] = None,
    ) -> str:
        """
        Validate and refine a draft answer against the retrieved context.

        Uses semantic validation to ensure the answer is properly grounded in
        the context and meets the question requirements.

        Args:
            question: User's original question
            draft_answer: Initial answer generated by _generate_answer
            context: Retrieved context used for answer generation
            llm_service: LLM service to use (defaults to self.llm_service)

        Returns:
            Validated and potentially refined answer

        Raises:
            Exception: If validation fails
        """
        service = llm_service or self.llm_service

        try:
            system_prompt = None
            if db is not None:
                system_prompt, _ = await get_active_self_check_prompt(db)
            if not system_prompt:
                raise RuntimeError("Active self-check prompt is not configured")

            user_prompt = self.SELF_CHECK_USER_TEMPLATE.format(
                question=question,
                draft_answer=draft_answer,
                context=context,
            )

            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt),
            ]

            response = await service.generate(
                messages=messages,
                temperature=0.0,  # Use deterministic validation
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )

            validated_answer = response.content.strip()

            logger.info(
                f"[SELF-CHECK] Validation complete: draft={len(draft_answer)} chars, "
                f"validated={len(validated_answer)} chars"
            )
            logger.info(
                f"✅ Self-check validation: draft={len(draft_answer)} chars, "
                f"validated={len(validated_answer)} chars"
            )

            return validated_answer

        except Exception:
            logger.exception("Self-check validation failed")
            # On validation failure, return the draft answer rather than failing entirely
            logger.warning("Returning draft answer due to validation failure")
            return draft_answer

    async def _extract_structure_filters(
        self, question: str, kb_id: UUID, db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Extract structure-based filters from query using LLM.

        Uses QueryIntentExtractor to understand queries like "show me question 2"
        and returns chunk range filters based on document structure (TOC).

        Args:
            question: User's question
            kb_id: Knowledge base ID
            db: Database session

        Returns:
            Filter dict for chunk_index range, or None for semantic search
        """
        try:
            # 1. Get list of documents in KB for context
            result = await db.execute(
                select(DocumentModel).where(
                    DocumentModel.knowledge_base_id == kb_id, DocumentModel.status == "completed"
                )
            )
            documents = result.scalars().all()

            if not documents:
                logger.debug("No completed documents in KB")
                return None

            doc_names = [doc.filename for doc in documents]
            logger.debug(f"KB documents: {doc_names}")

            # 2. Extract intent using LLM
            intent_extractor = get_query_intent_extractor()
            intent = await intent_extractor.extract_intent(
                query=question, kb_documents=doc_names, use_cache=True  # Use fast pattern fallback
            )

            logger.debug(
                f"Intent extracted: type={intent.intent_type}, confidence={intent.confidence}, doc={intent.document_name}, section={intent.section_type} {intent.section_number}"
            )

            logger.info(
                f"Extracted intent: type={intent.intent_type}, "
                f"doc={intent.document_name}, "
                f"section_type={intent.section_type}, "
                f"section_num={intent.section_number}, "
                f"confidence={intent.confidence:.2f}"
            )

            # 3. If not structured search or low confidence, fall back to semantic
            if intent.intent_type != "structured_search" or intent.confidence < 0.6:
                logger.debug("Intent not structured or confidence too low, using semantic search")
                return None

            # 4. Find document by name if specified
            target_doc = None
            preselected_section = None
            if intent.document_name:
                for doc in documents:
                    if intent.document_name.lower() in doc.filename.lower():
                        target_doc = doc
                        break

                if not target_doc:
                    logger.warning(f"Document '{intent.document_name}' not found in KB")
                    # Fall through to section-based matching across all docs
            else:
                # No specific document mentioned - find best matching document
                if len(documents) == 1:
                    target_doc = documents[0]
                    logger.debug(f"Using single document: {target_doc.filename}")
                else:
                    # Multiple documents - match document type to query section type
                    logger.debug(
                        f"Multiple documents ({len(documents)}), finding best match for section_type={intent.section_type}"
                    )

                    # Map section types to document types
                    section_to_doc_type = {
                        "question": "tma_questions",
                        "section": "textbook_chapter",
                        "chapter": "textbook_chapter",
                    }

                    preferred_doc_type = section_to_doc_type.get(intent.section_type)

                    # First pass: try to find document with matching type AND structure
                    if preferred_doc_type:
                        logger.debug(f"Looking for document_type={preferred_doc_type}")
                        for doc in documents:
                            analyzer = get_document_analyzer()
                            structure = await analyzer.get_structure(doc.id, db)
                            if structure and structure.document_type == preferred_doc_type:
                                target_doc = doc
                                logger.debug(
                                    f"Found matching document: {doc.filename} (type={structure.document_type})"
                                )
                                break

                    # Second pass: if no match, take any document with structure
                    if not target_doc:
                        logger.debug("No matching type found, trying any document with structure")
                        for doc in documents:
                            analyzer = get_document_analyzer()
                            structure = await analyzer.get_structure(doc.id, db)
                            if structure and structure.toc_json:
                                target_doc = doc
                                logger.debug(f"Found document with structure: {doc.filename}")
                                break

                    # Last resort: use first document
                    if not target_doc:
                        target_doc = documents[0]
                        logger.debug(
                            f"No document with structure, using first: {target_doc.filename}"
                        )

            # If we still don't have a document, try to locate one by section match
            if (
                not target_doc
                and intent.section_type
                and (intent.section_number is not None or intent.section_id)
            ):
                logger.debug("No document selected, scanning for matching section across documents")
                analyzer = get_document_analyzer()
                for doc in documents:
                    structure = await analyzer.get_structure(doc.id, db)
                    if not structure or not structure.toc_json:
                        continue
                    import json

                    toc_sections = json.loads(structure.toc_json)
                    candidate = self._find_matching_section(
                        toc_sections, intent.section_type, intent.section_number, intent.section_id
                    )
                    if candidate:
                        target_doc = doc
                        preselected_section = candidate
                        logger.debug(f"Found section match in document: {doc.filename}")
                        break

            if not target_doc:
                logger.debug("No specific document identified, using semantic search")
                return None

            # 5. Get document structure
            analyzer = get_document_analyzer()
            structure = await analyzer.get_structure(target_doc.id, db)

            if not structure or not structure.toc_json:
                logger.debug(f"No structure found for document {target_doc.filename}")
                return None

            # 6. Parse TOC and find matching section
            import json

            toc_sections = json.loads(structure.toc_json)
            matching_section = preselected_section or self._find_matching_section(
                toc_sections, intent.section_type, intent.section_number, intent.section_id
            )

            if not matching_section:
                logger.warning(
                    f"No matching section found for {intent.section_type} "
                    f"{intent.section_number or intent.section_id}"
                )
                return None

            # 7. Create chunk range filter
            chunk_start = matching_section.get("chunk_start")
            chunk_end = matching_section.get("chunk_end")

            if chunk_start is None or chunk_end is None:
                logger.warning("Section found but missing chunk range")
                return None

            logger.info(
                f"Found section '{matching_section.get('title')}': "
                f"chunks {chunk_start}-{chunk_end}"
            )

            # Return filter for chunk_index range + document_id
            return {
                "chunk_index": {"gte": chunk_start, "lte": chunk_end},
                "document_id": str(target_doc.id),
            }

        except Exception as e:
            logger.error(f"Structure filter extraction failed: {e}")
            return None

    def _find_matching_section(
        self,
        sections: List[Dict[str, Any]],
        section_type: Optional[str],
        section_number: Optional[int],
        section_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching section in TOC.

        Recursively searches through sections and subsections.

        Args:
            sections: List of TOC sections
            section_type: Type (question, section, chapter)
            section_number: Number if applicable
            section_id: ID like "1.2" for hierarchical sections

        Returns:
            Matching section dict or None
        """
        for section in sections:
            # Match by type and number
            if section_type and section.get("type") == section_type:
                # Check for question/chapter number match
                if section_number is not None:
                    metadata = section.get("metadata", {})
                    if metadata.get("question_number") == section_number:
                        return section

                # Check for section ID match (e.g., "1.2")
                if section_id and section.get("id") == f"section_{section_id.replace('.', '_')}":
                    return section

            # Recursively search subsections
            subsections = section.get("subsections", [])
            if subsections:
                match = self._find_matching_section(
                    subsections, section_type, section_number, section_id
                )
                if match:
                    return match

        return None

    async def close(self):
        """Close the LLM service."""
        await self.llm_service.close()
        logger.info("RAGService closed")


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get or create singleton instance of RAGService.

    Returns:
        RAGService instance
    """
    global _rag_service

    if _rag_service is None:
        _rag_service = RAGService()

    return _rag_service


async def close_rag_service():
    """Close the singleton RAG service."""
    global _rag_service

    if _rag_service is not None:
        await _rag_service.close()
        _rag_service = None
