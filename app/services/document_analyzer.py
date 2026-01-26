"""
Document Structure Analyzer Service.

Analyzes document structure using LLM to create table of contents.
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentStructure
from app.models.schemas import TOCSection, DocumentStructureAnalysis
from app.core.llm_factory import create_llm_service
from app.core.llm_base import Message
from app.core.vector_store import get_vector_store
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """Service for analyzing document structure."""

    ANALYSIS_PROMPT = """Analyze this document and create a hierarchical table of contents.

Document: {filename}
Total chunks: {total_chunks}

Content (first chunks):
{content}

Your task:
1. Identify the document type (e.g., "tma_questions", "textbook_chapter", "lecture_notes", "documentation")
2. Create a FLAT structure with minimal nesting - prioritize main sections over subsections
3. Map each section to chunk ranges (chunk_start, chunk_end)
4. Extract relevant metadata (e.g., marks for questions, section numbers)

IMPORTANT RULES:
- For TMA/assessment documents: Create ONE section per numbered question (Question 1, Question 2, etc.)
- DO NOT create separate subsections for parts like (a), (b), (i), (ii) - include them in the parent question
- DO NOT group multiple questions together (e.g., "Questions 3-5") - split them into individual sections
- Keep structure flat and simple - only use subsections for major divisions
- Each main question/chapter/section should be its own top-level section

Patterns to look for:
- Numbered questions: "Question 1", "Q1:", "Exercise 1.2" → Each is a separate section
- Sections: "Section 1.1", "Chapter 3", "Part A"
- Headers: submission instructions, warnings, etc.

Return ONLY valid JSON in this exact format:
{{
  "document_type": "tma_questions",
  "description": "TMA assessment with 6 numbered questions",
  "sections": [
    {{
      "id": "header",
      "title": "Header and Instructions",
      "type": "header",
      "chunk_start": 0,
      "chunk_end": 3,
      "metadata": {{}},
      "subsections": []
    }},
    {{
      "id": "question_1",
      "title": "Question 1 - GMC",
      "type": "question",
      "chunk_start": 4,
      "chunk_end": 5,
      "metadata": {{"marks": 10, "question_number": 1}},
      "subsections": []
    }},
    {{
      "id": "question_2",
      "title": "Question 2 - Calculations",
      "type": "question",
      "chunk_start": 5,
      "chunk_end": 7,
      "metadata": {{"marks": 30, "question_number": 2}},
      "subsections": [
        {{
          "id": "question_2a",
          "title": "(a) Pavlova recipe",
          "type": "sub_question",
          "chunk_start": 5,
          "chunk_end": 5,
          "metadata": {{}},
          "subsections": []
        }}
      ]
    }}
  ]
}}"""

    async def analyze_document(
        self,
        document_id: UUID,
        db: AsyncSession,
        collection_name: str,
        llm_model: Optional[str] = None,
    ) -> DocumentStructureAnalysis:
        """
        Analyze document structure using LLM.

        Args:
            document_id: Document ID to analyze
            db: Database session
            collection_name: Qdrant collection name
            llm_model: LLM model to use (default: cheap Haiku for cost efficiency)

        Returns:
            DocumentStructureAnalysis with TOC

        Raises:
            ValueError: If document not found
            Exception: If analysis fails
        """
        # Get document from DB
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        logger.info(f"Analyzing structure of document: {document.filename}")

        # Get chunks from Qdrant
        vector_store = get_vector_store()
        chunks = await self._get_document_chunks(
            vector_store,
            collection_name,
            document_id
        )

        if not chunks:
            raise ValueError(f"No chunks found for document {document_id}")

        # Prepare content sample (configurable limits)
        content_sample = self._prepare_content_sample(chunks)

        # Use configured LLM model (default: gpt-4o for better rate limits and cost)
        model = llm_model or settings.STRUCTURE_ANALYSIS_LLM_MODEL
        logger.info(f"Using {model} for document structure analysis ({len(chunks)} chunks)")
        llm_service = create_llm_service(model=model)
        prompt = self.ANALYSIS_PROMPT.format(
            filename=document.filename,
            total_chunks=len(chunks),
            content=content_sample
        )

        try:
            response = await llm_service.generate(
                messages=[
                    Message(role="system", content="You are a document structure analyzer. Return only valid JSON."),
                    Message(role="user", content=prompt)
                ],
                temperature=settings.STRUCTURE_ANALYSIS_LLM_TEMPERATURE,
            )

            # Parse JSON response
            analysis_data = self._parse_llm_response(response.content)

            # Create analysis object
            analysis = DocumentStructureAnalysis(
                document_type=analysis_data["document_type"],
                description=analysis_data["description"],
                sections=[TOCSection(**section) for section in analysis_data["sections"]],
                total_sections=len(analysis_data["sections"])
            )

            logger.info(
                f"✅ Analysis complete: {analysis.document_type}, "
                f"{analysis.total_sections} sections found"
            )

            # Log section titles for debugging
            section_titles = [s.title for s in analysis.sections]
            logger.info(f"📋 Sections: {section_titles}")

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze document structure: {e}")
            raise

        finally:
            await llm_service.close()

    async def save_structure(
        self,
        document_id: UUID,
        analysis: DocumentStructureAnalysis,
        db: AsyncSession,
        approved: bool = False
    ) -> DocumentStructure:
        """
        Save analyzed structure to database.

        Args:
            document_id: Document ID
            analysis: Analysis result
            db: Database session
            approved: Whether structure is user-approved

        Returns:
            Saved DocumentStructure
        """
        # Convert sections to JSON
        sections_dict = [section.model_dump() for section in analysis.sections]
        toc_json = json.dumps(sections_dict, indent=2)

        # Check if structure already exists
        result = await db.execute(
            select(DocumentStructure).where(
                DocumentStructure.document_id == document_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.toc_json = toc_json
            existing.document_type = analysis.document_type
            existing.approved_by_user = approved
            structure = existing
        else:
            # Create new
            structure = DocumentStructure(
                document_id=document_id,
                toc_json=toc_json,
                document_type=analysis.document_type,
                approved_by_user=approved
            )
            db.add(structure)

        await db.commit()
        await db.refresh(structure)

        logger.info(f"Saved structure for document {document_id}")
        return structure

    async def get_structure(
        self,
        document_id: UUID,
        db: AsyncSession
    ) -> Optional[DocumentStructure]:
        """Get document structure from database."""
        result = await db.execute(
            select(DocumentStructure).where(
                DocumentStructure.document_id == document_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_document_chunks(
        self,
        vector_store,
        collection_name: str,
        document_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Retrieve ALL document chunks from Qdrant with pagination.

        Handles documents with >100 chunks by scrolling until next_offset is None.
        """
        chunks = []
        next_offset = None

        # Scroll through ALL points for this document (handle pagination)
        while True:
            points, next_offset = await vector_store.client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"value": str(document_id)}
                        }
                    ]
                },
                limit=settings.STRUCTURE_ANALYSIS_QDRANT_PAGE_SIZE,
                offset=next_offset,
                with_payload=True,
                with_vectors=False
            )

            for point in points:
                payload = point.payload
                chunks.append({
                    "index": payload.get("chunk_index", 0),
                    "text": payload.get("text", ""),
                    "metadata": payload
                })

            # Break if no more results
            if next_offset is None:
                break

        # Sort by chunk index
        chunks.sort(key=lambda x: x["index"])

        logger.debug(f"Retrieved {len(chunks)} chunks for document {document_id}")
        return chunks

    def _prepare_content_sample(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Prepare content sample for LLM analysis.

        Uses configurable limits from settings:
        - STRUCTURE_ANALYSIS_MAX_CHUNKS (0 = all chunks)
        - STRUCTURE_ANALYSIS_MAX_CHARS_PER_CHUNK (0 = full chunk)
        - STRUCTURE_ANALYSIS_MAX_TOTAL_CHARS (overall limit)
        """
        # Apply chunk limit (0 means all chunks)
        max_chunks = settings.STRUCTURE_ANALYSIS_MAX_CHUNKS
        sample_chunks = chunks[:max_chunks] if max_chunks > 0 else chunks

        # Apply per-chunk char limit (0 means full chunk)
        max_chars_per_chunk = settings.STRUCTURE_ANALYSIS_MAX_CHARS_PER_CHUNK
        lines = []

        for chunk in sample_chunks:
            lines.append(f"[Chunk {chunk['index']}]")
            text = chunk["text"]
            if max_chars_per_chunk > 0:
                text = text[:max_chars_per_chunk]
            lines.append(text)
            lines.append("")  # Empty line separator

        content = "\n".join(lines)

        # Apply total char limit (0 = unlimited)
        max_total = settings.STRUCTURE_ANALYSIS_MAX_TOTAL_CHARS
        if max_total > 0 and len(content) > max_total:
            content = content[:max_total] + "\n... (truncated)"
            logger.warning(
                f"Content truncated to {max_total} chars "
                f"(from {len(content)} chars, {len(sample_chunks)} chunks)"
            )

        logger.debug(
            f"Prepared content sample: {len(content)} chars, "
            f"{len(sample_chunks)}/{len(chunks)} chunks"
        )

        return content

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response."""
        # Try to extract JSON from response
        # Sometimes LLM adds markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")


# Singleton instance
_analyzer: Optional[DocumentAnalyzer] = None


def get_document_analyzer() -> DocumentAnalyzer:
    """Get or create singleton instance of DocumentAnalyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = DocumentAnalyzer()
    return _analyzer
