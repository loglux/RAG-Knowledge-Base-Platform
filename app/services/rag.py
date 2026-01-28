"""
RAG (Retrieval-Augmented Generation) Service.

Combines retrieval and generation for question answering over knowledge bases.
"""
import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.retrieval import get_retrieval_engine, RetrievalEngine, RetrievedChunk
from app.core.llm_factory import create_llm_service
from app.core.llm_base import BaseLLMService, Message
from app.services.query_intent import get_query_intent_extractor, QueryIntent
from app.services.document_analyzer import get_document_analyzer
from app.models.database import Document as DocumentModel


logger = logging.getLogger(__name__)


class RAGResponse(BaseModel):
    """Response from RAG system."""

    answer: str = Field(..., description="Generated answer")
    sources: List[RetrievedChunk] = Field(..., description="Source chunks used")
    query: str = Field(..., description="Original query")
    context_used: str = Field(..., description="Context provided to LLM")
    model: str = Field(..., description="Model used for generation")

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

    # System prompt for RAG (kept for rollback)
    SYSTEM_PROMPT_LEGACY = """You are a helpful AI assistant that answers questions based on the provided context from a knowledge base.

Your task:
1. First, understand the FULL CONVERSATION HISTORY to grasp what the user is asking about
2. Pay attention to pronouns (it, this, that, these) - they often refer to topics from previous messages
3. Use the knowledge base context to provide accurate, detailed answers
4. Answer based ONLY on information from the knowledge base context
5. Be concise unless the user asks to show/quote content or examples
6. Reference specific sources when appropriate (e.g., "According to Source 1...")

Important:
- The conversation may contain follow-up questions - use previous messages to understand the current question
- Pronouns like "it", "this", "that" refer to topics mentioned earlier in the conversation
- Do NOT make up information not present in the context
- If the context doesn't contain enough information, say so clearly
- If the user asks to show a question, return the full verbatim text from the context.
- If the requested item spans multiple context chunks, return all relevant verbatim excerpts,
  even if they come from multiple chunks, until the item is complete.
- Do not invent missing parts or add commentary.
"""
    # System prompt for RAG (incremental update)
    SYSTEM_PROMPT = """Identity:
You are a retrieval assistant for a knowledge base. You answer ONLY from the provided context.

""" + SYSTEM_PROMPT_LEGACY + """

Context follows below.
"""

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
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_context_chars: Optional[int] = None,
        score_threshold: Optional[float] = None,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_structure: bool = False,
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
            temperature: LLM temperature (0-2)
            max_tokens: Maximum tokens in response
            llm_model: Override LLM model for this query
            llm_provider: Override LLM provider for this query
            conversation_history: Previous messages for follow-up questions
            use_structure: Use document structure for structured search (default: False)
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

            logger.warning(f"[DEBUG] RAG query with use_structure={use_structure}, db={db is not None}, kb_id={kb_id}")

            if use_structure:
                if not db or not kb_id:
                    logger.warning("use_structure=True but db or kb_id not provided, falling back to semantic search")
                else:
                    logger.warning("[DEBUG] Extracting structure filters...")
                    chunk_filters = await self._extract_structure_filters(
                        question=question,
                        kb_id=kb_id,
                        db=db
                    )
                    if chunk_filters:
                        logger.warning(f"[DEBUG] Structure-based search: {chunk_filters}")
                    else:
                        logger.warning("[DEBUG] Structure filters returned None, using semantic search")

            # 2. Retrieve relevant chunks (with optional structure filters)
            if mode == "hybrid":
                if not kb_id:
                    logger.warning("Hybrid retrieval requires kb_id, falling back to dense search")
                    mode = "dense"

            if mode == "hybrid":
                logger.debug(f"Hybrid retrieval (top_k={top_k}, lexical_top_k={lexical_top_k})")
                retrieval_result = await self.retrieval.retrieve_hybrid(
                    query=question,
                    collection_name=collection_name,
                    embedding_model=embedding_model,
                    knowledge_base_id=str(kb_id),
                    top_k=top_k,
                    lexical_top_k=lexical_top_k,
                    score_threshold=score_threshold,
                    filters=chunk_filters,
                    dense_weight=dense_weight,
                    lexical_weight=lexical_weight,
                )
            else:
                logger.debug(f"Retrieving top {top_k} chunks using {embedding_model}")
                retrieval_result = await self.retrieval.retrieve(
                    query=question,
                    collection_name=collection_name,
                    embedding_model=embedding_model,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    filters=chunk_filters,
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

            # 3. Generate answer with context
            context = retrieval_result.context
            if max_context_chars is not None:
                context = self.retrieval._assemble_context(
                    retrieval_result.chunks,
                    max_length=max_context_chars,
                )
            elif chunk_filters:
                # For structured question retrieval, avoid truncating the target section.
                context = self.retrieval._assemble_context(
                    retrieval_result.chunks,
                    max_length=max_context_chars,
                )
            logger.debug(f"Generating answer with {len(retrieval_result.chunks)} chunks")
            answer = await self._generate_answer(
                question=question,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
                llm_service=llm_service,
                conversation_history=conversation_history,
            )

            logger.info(
                f"RAG completed: {len(answer)} chars answer from {len(retrieval_result.chunks)} sources"
            )

            return RAGResponse(
                answer=answer,
                sources=retrieval_result.chunks,
                query=question,
                context_used=context,
                model=llm_service.model,
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
            answer = await self._generate_answer(
                question=question,
                context=retrieval_result.context,
                llm_service=self.llm_service,
            )

            return RAGResponse(
                answer=answer,
                sources=retrieval_result.chunks,
                query=question,
                context_used=retrieval_result.context,
                model=self.llm_service.model,
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
    ) -> str:
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
            Generated answer text

        Raises:
            Exception: If generation fails
        """
        service = llm_service or self.llm_service

        try:
            # Build messages list starting with system prompt
            messages = [Message(role="system", content=self.SYSTEM_PROMPT)]

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

            user_prompt = f"""<context>
{context}
</context>

<question>{question}{show_question_instructions}</question>

Answer based on the context above:"""

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

            return answer

        except Exception:
            logger.exception("Answer generation failed")
            raise

    async def _extract_structure_filters(
        self,
        question: str,
        kb_id: UUID,
        db: AsyncSession
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
                    DocumentModel.knowledge_base_id == kb_id,
                    DocumentModel.status == "completed"
                )
            )
            documents = result.scalars().all()

            if not documents:
                logger.warning("[DEBUG] No completed documents in KB")
                return None

            doc_names = [doc.filename for doc in documents]
            logger.warning(f"[DEBUG] KB documents: {doc_names}")

            # 2. Extract intent using LLM
            intent_extractor = get_query_intent_extractor()
            intent = await intent_extractor.extract_intent(
                query=question,
                kb_documents=doc_names,
                use_cache=True  # Use fast pattern fallback
            )

            logger.warning(f"[DEBUG] Intent extracted: type={intent.intent_type}, confidence={intent.confidence}, doc={intent.document_name}, section={intent.section_type} {intent.section_number}")

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
            if intent.document_name:
                for doc in documents:
                    if intent.document_name.lower() in doc.filename.lower():
                        target_doc = doc
                        break

                if not target_doc:
                    logger.warning(f"Document '{intent.document_name}' not found in KB")
                    return None
            else:
                # No specific document mentioned - find best matching document
                if len(documents) == 1:
                    target_doc = documents[0]
                    logger.warning(f"[DEBUG] Using single document: {target_doc.filename}")
                else:
                    # Multiple documents - match document type to query section type
                    logger.warning(f"[DEBUG] Multiple documents ({len(documents)}), finding best match for section_type={intent.section_type}")

                    # Map section types to document types
                    section_to_doc_type = {
                        "question": "tma_questions",
                        "section": "textbook_chapter",
                        "chapter": "textbook_chapter",
                    }

                    preferred_doc_type = section_to_doc_type.get(intent.section_type)

                    # First pass: try to find document with matching type AND structure
                    if preferred_doc_type:
                        logger.warning(f"[DEBUG] Looking for document_type={preferred_doc_type}")
                        for doc in documents:
                            analyzer = get_document_analyzer()
                            structure = await analyzer.get_structure(doc.id, db)
                            if structure and structure.document_type == preferred_doc_type:
                                target_doc = doc
                                logger.warning(f"[DEBUG] Found matching document: {doc.filename} (type={structure.document_type})")
                                break

                    # Second pass: if no match, take any document with structure
                    if not target_doc:
                        logger.warning(f"[DEBUG] No matching type found, trying any document with structure")
                        for doc in documents:
                            analyzer = get_document_analyzer()
                            structure = await analyzer.get_structure(doc.id, db)
                            if structure and structure.toc_json:
                                target_doc = doc
                                logger.warning(f"[DEBUG] Found document with structure: {doc.filename}")
                                break

                    # Last resort: use first document
                    if not target_doc:
                        target_doc = documents[0]
                        logger.warning(f"[DEBUG] No document with structure, using first: {target_doc.filename}")

            if not target_doc:
                logger.warning("[DEBUG] No specific document identified, using semantic search")
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
            matching_section = self._find_matching_section(
                toc_sections,
                intent.section_type,
                intent.section_number,
                intent.section_id
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
                "document_id": str(target_doc.id)
            }

        except Exception as e:
            logger.error(f"Structure filter extraction failed: {e}")
            return None

    def _find_matching_section(
        self,
        sections: List[Dict[str, Any]],
        section_type: Optional[str],
        section_number: Optional[int],
        section_id: Optional[str]
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
                    subsections,
                    section_type,
                    section_number,
                    section_id
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
