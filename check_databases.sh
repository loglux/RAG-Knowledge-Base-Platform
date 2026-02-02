#!/bin/bash

echo "========================================="
echo "DATABASE VERIFICATION REPORT"
echo "========================================="
echo ""

echo "1. POSTGRESQL - Knowledge Bases"
echo "-----------------------------------------"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t -c "
SELECT
    'Total KBs: ' || COUNT(*)::text
FROM knowledge_bases;
"

echo ""
echo "2. POSTGRESQL - Documents Count"
echo "-----------------------------------------"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t -c "
SELECT
    'Total Documents: ' || COUNT(*)::text
FROM documents;
"

echo ""
echo "3. POSTGRESQL - Chunks Count"
echo "-----------------------------------------"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t -c "
SELECT
    'Total Chunks: ' || COUNT(*)::text
FROM chunks;
"

echo ""
echo "4. QDRANT - Collections"
echo "-----------------------------------------"
docker exec kb-platform-backend-prod curl -s http://qdrant:6333/collections | jq -r '
.result.collections |
"Total Collections: " + (. | length | tostring)
'

echo ""
echo "5. KB WITH MISSING QDRANT COLLECTIONS"
echo "-----------------------------------------"
echo "Checking each KB for Qdrant collection..."

# Get all KB IDs
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t -A -c "
SELECT id FROM knowledge_bases ORDER BY created_at;
" | while read kb_id; do
    # Convert UUID to collection name format (remove hyphens)
    collection_name="kb_$(echo $kb_id | tr -d '-')"

    # Check if collection exists in Qdrant
    exists=$(docker exec kb-platform-backend-prod curl -s http://qdrant:6333/collections/$collection_name 2>/dev/null | jq -r '.result.status // "missing"')

    if [ "$exists" = "missing" ] || [ "$exists" = "null" ]; then
        # Get KB name and doc count
        kb_info=$(docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t -A -c "
        SELECT
            kb.name || '|' || COALESCE(COUNT(d.id), 0)::text
        FROM knowledge_bases kb
        LEFT JOIN documents d ON kb.id = d.knowledge_base_id
        WHERE kb.id = '$kb_id'
        GROUP BY kb.name;
        ")

        kb_name=$(echo $kb_info | cut -d'|' -f1)
        doc_count=$(echo $kb_info | cut -d'|' -f2)

        echo "  ❌ $kb_name ($doc_count docs) - Collection: $collection_name [MISSING]"
    fi
done

echo ""
echo "6. DETAILED KB STATUS"
echo "-----------------------------------------"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -c "
SELECT
    kb.name,
    COUNT(d.id) as docs,
    kb.embedding_model,
    kb.chunking_strategy,
    DATE(kb.created_at) as created
FROM knowledge_bases kb
LEFT JOIN documents d ON kb.id = d.knowledge_base_id
GROUP BY kb.id, kb.name, kb.embedding_model, kb.chunking_strategy, kb.created_at
ORDER BY kb.created_at;
"

echo ""
echo "7. OPENSEARCH INDICES"
echo "-----------------------------------------"
docker exec kb-platform-backend-prod curl -s http://opensearch:9200/_cat/indices?v | grep "kb_"

echo ""
echo "========================================="
echo "VERIFICATION COMPLETE"
echo "========================================="
