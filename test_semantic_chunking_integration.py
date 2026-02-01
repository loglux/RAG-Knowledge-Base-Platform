#!/usr/bin/env python3
"""
Integration test for SemanticChunking class.

Tests the production SemanticChunking implementation.
"""
from app.services.chunking import SemanticChunking
from test_texts import AI_HISTORY_TEXT


def test_semantic_chunking():
    """Test SemanticChunking with AI history text."""
    print("=" * 80)
    print("SEMANTIC CHUNKING INTEGRATION TEST")
    print("=" * 80)
    print()

    # Initialize SemanticChunking
    # Test without contextual embeddings first (faster)
    print("Test 1: Without Contextual Embeddings")
    print("-" * 80)

    chunker = SemanticChunking(
        chunk_size=600,
        boundary_method="adaptive",
        merge_similarity_threshold=0.35,
        min_chunk_size=100,
        use_contextual_embeddings=False,  # Disable for faster test
    )

    # Split text
    chunks = chunker.split(AI_HISTORY_TEXT)

    print(f"Created {len(chunks)} chunks\n")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1} ({chunk.char_count} chars, words: {chunk.word_count}):")
        print(f"  Preview: {chunk.content[:100]}...")
        print()

    # Statistics
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)
    avg_size = sum(c.char_count for c in chunks) / len(chunks)
    print(f"Total chunks: {len(chunks)}")
    print(f"Avg size: {avg_size:.0f} chars")
    print(f"Min size: {min(c.char_count for c in chunks)} chars")
    print(f"Max size: {max(c.char_count for c in chunks)} chars")
    print()

    # Test 2: With Contextual Embeddings (optional - slower)
    run_contextual = input("Run test with Contextual Embeddings? (y/n): ")

    if run_contextual.lower() == 'y':
        print("\n" + "=" * 80)
        print("Test 2: With Contextual Embeddings")
        print("-" * 80)

        chunker_contextual = SemanticChunking(
            chunk_size=600,
            boundary_method="adaptive",
            merge_similarity_threshold=0.35,
            min_chunk_size=100,
            use_contextual_embeddings=True,
        )

        chunks_contextual = chunker_contextual.split(AI_HISTORY_TEXT)

        print(f"\nCreated {len(chunks_contextual)} chunks with contextual descriptions\n")

        for i, chunk in enumerate(chunks_contextual):
            print(f"Chunk {i + 1} ({chunk.char_count} chars):")
            print(f"  Content: {chunk.content[:80]}...")
            if "contextual_description" in chunk.metadata:
                print(f"  Context: {chunk.metadata['contextual_description'][:150]}...")
            print()

    print("=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    test_semantic_chunking()
