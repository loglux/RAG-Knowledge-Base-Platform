#!/usr/bin/env python3
"""
Semantic Chunking Prototype Test

Tests the concept of using embeddings to find semantic boundaries in text.
"""
import asyncio
import os
import sys
from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from test_texts import SIMPLE_TEXT, AI_HISTORY_TEXT, TECHNICAL_TEXT

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print("Downloading NLTK punkt_tab tokenizer...")
    nltk.download('punkt_tab')


async def test_semantic_chunking(test_name: str = "simple"):
    """Test semantic chunking concept with a sample document.

    Args:
        test_name: Which test to run ("simple", "ai_history", "technical")
    """

    # Select test text
    test_texts = {
        "simple": SIMPLE_TEXT,
        "ai_history": AI_HISTORY_TEXT,
        "technical": TECHNICAL_TEXT
    }

    text = test_texts.get(test_name, SIMPLE_TEXT)

    print("=" * 80)
    print("SEMANTIC CHUNKING PROTOTYPE TEST")
    print(f"Test: {test_name.upper()}")
    print("=" * 80)
    print()

    # Step 1: Split into sentences
    print("Step 1: Splitting text into sentences...")
    sentences = nltk.sent_tokenize(text.strip(), language='russian')
    print(f"Found {len(sentences)} sentences:")
    for i, sent in enumerate(sentences):
        print(f"  [{i}] {sent[:60]}...")
    print()

    # Step 2: Get embeddings for each sentence
    print("Step 2: Getting embeddings for each sentence...")
    print("Using OpenAI text-embedding-3-small...")

    # Import our embeddings service
    from app.core.embeddings_factory import create_embedding_service

    embeddings_service = create_embedding_service(
        model="text-embedding-3-small"  # Provider auto-detected from model name
    )

    embeddings = []
    for i, sent in enumerate(sentences):
        embedding = await embeddings_service.generate_embedding(sent)
        embeddings.append(embedding)
        print(f"  [{i}] Embedded ({len(embedding)} dims)")
    print()

    # Step 3: Calculate cosine similarity between consecutive sentences
    print("Step 3: Calculating similarity between consecutive sentences...")
    similarities = []
    for i in range(len(embeddings) - 1):
        # Reshape for sklearn
        emb1 = np.array(embeddings[i]).reshape(1, -1)
        emb2 = np.array(embeddings[i + 1]).reshape(1, -1)

        sim = cosine_similarity(emb1, emb2)[0][0]
        similarities.append(sim)

        print(f"  Similarity [{i}] <-> [{i+1}]: {sim:.4f}")
        print(f"    [{i}]: {sentences[i][:50]}...")
        print(f"    [{i+1}]: {sentences[i+1][:50]}...")
        print()

    # Step 4: Find semantic boundaries
    print("Step 4: Finding semantic boundaries...")

    # Boundary detection method: "fixed" or "adaptive"
    BOUNDARY_METHOD = "adaptive"  # Change to "fixed" for fixed threshold

    if BOUNDARY_METHOD == "fixed":
        threshold = 0.30  # Fixed threshold for all texts
        print(f"Using FIXED threshold: {threshold}")
    else:  # adaptive
        # Adaptive threshold based on text statistics
        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        k = 1.0  # Sensitivity coefficient (higher = fewer boundaries)
        threshold = mean_sim - k * std_sim
        print(f"Using ADAPTIVE threshold:")
        print(f"  Mean similarity: {mean_sim:.4f}")
        print(f"  Std deviation: {std_sim:.4f}")
        print(f"  Threshold = mean - {k} * std = {threshold:.4f}")

    print()

    boundaries = []
    for i, sim in enumerate(similarities):
        if sim < threshold:
            boundaries.append(i + 1)  # Boundary AFTER sentence i
            print(f"  🔴 BOUNDARY at position {i+1} (similarity: {sim:.4f})")
        else:
            print(f"  ✅ Same topic at position {i+1} (similarity: {sim:.4f})")
    print()

    # Step 5: Group sentences into chunks (initial)
    print("Step 5: Grouping sentences into semantic chunks (initial)...")
    chunks = []
    current_chunk = []

    for i, sent in enumerate(sentences):
        current_chunk.append(sent)
        if i + 1 in boundaries or i == len(sentences) - 1:
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    print(f"Created {len(chunks)} initial chunks")
    print()

    # Step 6: Smart balancing - get chunk embeddings first
    print("Step 6: Getting embeddings for chunks...")
    chunk_embeddings = []
    for i, chunk in enumerate(chunks):
        embedding = await embeddings_service.generate_embedding(chunk)
        chunk_embeddings.append(embedding)
        print(f"  Chunk {i+1}: Embedded ({len(embedding)} dims, {len(chunk)} chars)")
    print()

    # Step 7: Smart balancing (merge only semantically similar chunks)
    print("Step 7: Smart balancing (merge only semantically similar chunks)...")
    MIN_CHUNK_SIZE = 200  # chars
    MAX_CHUNK_SIZE = 600  # chars
    MERGE_SIMILARITY_THRESHOLD = 0.35  # Only merge if similarity > this

    balanced_chunks = []
    balanced_embeddings = []
    i = 0

    while i < len(chunks):
        current = chunks[i]
        current_embedding = chunk_embeddings[i]

        # If chunk is too small, check if we can merge with next
        if len(current) < MIN_CHUNK_SIZE and i + 1 < len(chunks):
            # Calculate similarity with next chunk
            next_embedding = chunk_embeddings[i + 1]
            emb1 = np.array(current_embedding).reshape(1, -1)
            emb2 = np.array(next_embedding).reshape(1, -1)
            similarity = cosine_similarity(emb1, emb2)[0][0]

            print(f"  Chunk {i+1} is small ({len(current)} chars)")
            print(f"    Similarity with next chunk: {similarity:.4f}")

            if similarity > MERGE_SIMILARITY_THRESHOLD:
                print(f"    ✅ Merging (similarity {similarity:.4f} > {MERGE_SIMILARITY_THRESHOLD})")
                # Merge and recalculate embedding
                merged = current + " " + chunks[i + 1]
                merged_embedding = await embeddings_service.generate_embedding(merged)
                current = merged
                current_embedding = merged_embedding
                i += 1  # Skip next chunk as we merged it
            else:
                print(f"    ❌ Not merging (similarity {similarity:.4f} ≤ {MERGE_SIMILARITY_THRESHOLD})")
                print(f"    → Keeping small chunk to preserve semantic boundary")

        # If chunk is too large, split it
        if len(current) > MAX_CHUNK_SIZE:
            print(f"  Chunk is large ({len(current)} chars), splitting...")
            # Split at sentence boundaries within the chunk
            chunk_sentences = nltk.sent_tokenize(current, language='russian')
            temp_chunk = []
            for sent in chunk_sentences:
                if len(" ".join(temp_chunk)) + len(sent) > MAX_CHUNK_SIZE and temp_chunk:
                    split_chunk = " ".join(temp_chunk)
                    split_embedding = await embeddings_service.generate_embedding(split_chunk)
                    balanced_chunks.append(split_chunk)
                    balanced_embeddings.append(split_embedding)
                    print(f"    → Created chunk of {len(split_chunk)} chars")
                    temp_chunk = [sent]
                else:
                    temp_chunk.append(sent)
            if temp_chunk:
                split_chunk = " ".join(temp_chunk)
                split_embedding = await embeddings_service.generate_embedding(split_chunk)
                balanced_chunks.append(split_chunk)
                balanced_embeddings.append(split_embedding)
                print(f"    → Created chunk of {len(split_chunk)} chars")
        else:
            balanced_chunks.append(current)
            balanced_embeddings.append(current_embedding)

        i += 1

    print(f"\nFinal smart-balanced chunks: {len(balanced_chunks)}")
    for i, chunk in enumerate(balanced_chunks):
        print(f"\n--- Smart-Balanced Chunk {i+1} ({len(chunk)} chars) ---")
        print(chunk)
    print()

    # Step 8: Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print(f"Total sentences: {len(sentences)}")
    print(f"Semantic boundaries found: {len(boundaries)}")
    print(f"Initial chunks: {len(chunks)}")
    print(f"Smart-balanced chunks: {len(balanced_chunks)}")
    print(f"Boundary detection method: {BOUNDARY_METHOD.upper()}")
    print(f"Sentence similarity threshold: {threshold:.4f}")
    print(f"Chunk merge similarity threshold: {MERGE_SIMILARITY_THRESHOLD}")
    print(f"Min chunk size: {MIN_CHUNK_SIZE} chars")
    print(f"Max chunk size: {MAX_CHUNK_SIZE} chars")
    print()
    print("Sentence similarity statistics:")
    print(f"  Mean: {np.mean(similarities):.4f}")
    print(f"  Std:  {np.std(similarities):.4f}")
    print(f"  Min:  {np.min(similarities):.4f}")
    print(f"  Max:  {np.max(similarities):.4f}")
    print()

    # Step 9: Compare with fixed-size chunking
    print("=" * 80)
    print("COMPARISON: Different Chunking Strategies")
    print("=" * 80)

    full_text = " ".join(sentences)
    chunk_size = 200

    fixed_chunks = []
    for i in range(0, len(full_text), chunk_size):
        fixed_chunks.append(full_text[i:i+chunk_size])

    print(f"\n1. Fixed-size chunking (size={chunk_size}):")
    print(f"   Chunks: {len(fixed_chunks)}")
    for i, chunk in enumerate(fixed_chunks):
        print(f"   Chunk {i+1}: {len(chunk)} chars")

    print(f"\n2. Semantic chunking (unbalanced):")
    print(f"   Chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"   Chunk {i+1}: {len(chunk)} chars")

    print(f"\n3. Semantic chunking (smart-balanced):")
    print(f"   Chunks: {len(balanced_chunks)}")
    for i, chunk in enumerate(balanced_chunks):
        print(f"   Chunk {i+1}: {len(chunk)} chars")

    print()
    print("=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    # Get test name from command line argument
    test_name = sys.argv[1] if len(sys.argv) > 1 else "simple"

    if test_name not in ["simple", "ai_history", "technical"]:
        print("Usage: python test_semantic_chunking.py [simple|ai_history|technical]")
        print("Default: simple")
        sys.exit(1)

    asyncio.run(test_semantic_chunking(test_name))
