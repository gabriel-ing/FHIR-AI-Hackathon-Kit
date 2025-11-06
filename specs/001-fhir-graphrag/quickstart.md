# Quick Start Guide: FHIR GraphRAG Knowledge Graph

**Feature**: 001-fhir-graphrag
**Date**: 2025-11-06
**Target Audience**: Developers and system administrators

---

## Overview

This guide provides step-by-step instructions for setting up and using the FHIR GraphRAG knowledge graph system. The system extracts medical entities and relationships from clinical notes in FHIR DocumentReference resources and enables multi-modal search combining vector similarity, text matching, and graph traversal.

**Estimated Setup Time**: 15-30 minutes

---

## Prerequisites

### Required Software

1. **InterSystems IRIS Database**
   - Running instance at localhost:32782
   - Namespace: DEMO
   - Credentials: _SYSTEM / ISCDEMO
   - Existing FHIR data: 51 DocumentReference resources

2. **Python Environment**
   - Python 3.12 or higher
   - Miniconda or virtualenv recommended

3. **rag-templates Library**
   - Location: `/Users/tdyar/ws/rag-templates`
   - Verify: `ls /Users/tdyar/ws/rag-templates/iris_rag`

### Optional Software

4. **Ollama LLM Service** (for enhanced entity extraction)
   - Install: `curl https://ollama.ai/install.sh | sh`
   - Pull model: `ollama pull gemma3:4b`
   - Verify: `ollama list`

### Pre-existing Components

The following components should already be in place from the existing FHIR AI Hackathon tutorial:

- ✅ FHIR native table: `HSFHIR_X0001_R.Rsrc` (2,739 resources)
- ✅ Vector table: `VectorSearch.FHIRResourceVectors` (51 DocumentReference vectors)
- ✅ Existing script: `direct_fhir_vector_approach.py` (vector search POC)
- ✅ Utilities: `Tutorial/Utils/get_iris_connection.py`

---

## Installation

### Step 1: Install Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install iris-python-driver sentence-transformers PyYAML pytest

# Verify rag-templates is accessible
export PYTHONPATH="/Users/tdyar/ws/rag-templates:$PYTHONPATH"
python3 -c "from iris_rag import create_pipeline; print('✅ rag-templates accessible')"
```

### Step 2: Create Configuration File

Create `config/fhir_graphrag_config.yaml`:

```bash
mkdir -p config
cp specs/001-fhir-graphrag/contracts/byot-config-schema.yaml config/fhir_graphrag_config.yaml
```

Edit `config/fhir_graphrag_config.yaml` and verify/update:
- Database credentials (username/password)
- FHIR table name (`HSFHIR_X0001_R.Rsrc`)
- Vector table name (`VectorSearch.FHIRResourceVectors`)
- LLM settings (if using Ollama)

### Step 3: Verify Database Connection

```bash
# Test IRIS connection
python3 <<EOF
import iris
conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM HSFHIR_X0001_R.Rsrc WHERE ResourceType='DocumentReference'")
count = cursor.fetchone()[0]
print(f"✅ Found {count} DocumentReference resources")
cursor.close()
conn.close()
EOF
```

Expected output: `✅ Found 51 DocumentReference resources`

---

## Knowledge Graph Build

### Step 1: Create Knowledge Graph Tables

Run the setup script to create `RAG.Entities` and `RAG.EntityRelationships` tables:

```bash
python3 src/setup/fhir_graphrag_setup.py --mode=init
```

This will:
- Create `RAG.Entities` table with indexes
- Create `RAG.EntityRelationships` table with indexes
- Validate FHIR table accessibility
- Report table creation status

**Expected Output**:
```
[INFO] Initializing GraphRAG knowledge graph tables...
[INFO] ✅ Created table RAG.Entities
[INFO] ✅ Created table RAG.EntityRelationships
[INFO] ✅ Created indexes on RAG.Entities
[INFO] ✅ Created indexes on RAG.EntityRelationships
[INFO] Initialization complete!
```

### Step 2: Extract Entities and Build Knowledge Graph

Process all 51 DocumentReference resources and extract medical entities:

```bash
python3 src/setup/fhir_graphrag_setup.py --mode=build
```

This will:
- Load BYOT configuration from `config/fhir_graphrag_config.yaml`
- Connect to IRIS database
- Query FHIR native tables for DocumentReference resources
- Decode hex-encoded clinical notes
- Extract medical entities (SYMPTOM, CONDITION, MEDICATION, etc.)
- Identify entity relationships (TREATS, CAUSES, etc.)
- Store entities and relationships in knowledge graph tables

**Expected Output**:
```
[INFO] Loading FHIR GraphRAG configuration...
[INFO] ✅ Configuration loaded from config/fhir_graphrag_config.yaml
[INFO] Connecting to IRIS database...
[INFO] ✅ Connected to localhost:32782, namespace DEMO
[INFO] Loading FHIR DocumentReference resources...
[INFO] ✅ Loaded 51 DocumentReference resources
[INFO] Processing document 1/51...
[INFO] ✅ Extracted 5 entities (SYMPTOM: 2, CONDITION: 1, MEDICATION: 2)
[INFO] ✅ Identified 3 relationships (TREATS: 2, CAUSES: 1)
...
[INFO] Processing document 51/51...
[INFO] ===== Knowledge Graph Build Complete =====
[INFO] Total entities extracted: 127
[INFO] Total relationships identified: 64
[INFO] Processing time: 3 minutes 42 seconds
[INFO] Average time per document: 4.4 seconds
```

**Performance Targets**:
- ✅ Entity extraction: < 2 seconds per document (regex-only) OR < 10 seconds (with LLM)
- ✅ Total build time: < 5 minutes for 51 documents
- ✅ Entities extracted: 100+ medical entities
- ✅ Relationships identified: 50+ entity relationships

### Step 3: Verify Knowledge Graph

Query the knowledge graph to verify successful build:

```bash
python3 <<EOF
import iris
conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
cursor = conn.cursor()

# Count entities by type
cursor.execute("""
SELECT EntityType, COUNT(*) as Count
FROM RAG.Entities
GROUP BY EntityType
ORDER BY Count DESC
""")
print("Entities by type:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Count relationships by type
cursor.execute("""
SELECT RelationshipType, COUNT(*) as Count
FROM RAG.EntityRelationships
GROUP BY RelationshipType
ORDER BY Count DESC
""")
print("\nRelationships by type:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

cursor.close()
conn.close()
EOF
```

---

## Multi-Modal Search Usage

### Basic Query

Run a multi-modal search query combining vector, text, and graph search:

```bash
python3 src/query/fhir_graphrag_query.py "respiratory symptoms"
```

**Expected Output**:
```
================================================================================
GraphRAG Query: respiratory symptoms
================================================================================

📊 Search Results:
   - Retrieved: 5 documents
   - Execution time: 0.842s
   - Retrieval method: rrf (vector + text + graph)

🔬 Extracted Entities:
   - cough (SYMPTOM)
   - shortness of breath (SYMPTOM)
   - chest congestion (SYMPTOM)
   - albuterol (MEDICATION)
   - asthma (CONDITION)

🔗 Relationships:
   - albuterol → TREATS → asthma
   - asthma → CAUSES → shortness of breath
   - cough → CO_OCCURS_WITH → chest congestion

💡 Answer:
   The patient has reported respiratory symptoms including cough, shortness of
   breath, and chest congestion. Medical history indicates asthma as an
   underlying condition, treated with albuterol inhaler.

📝 Sources:
   1. DocumentReference/12 (Patient/3, 2023-05-15)
   2. DocumentReference/23 (Patient/3, 2023-06-01)
   3. DocumentReference/34 (Patient/3, 2023-06-15)

================================================================================
```

### Patient-Specific Query

Filter results to a specific patient:

```bash
python3 src/query/fhir_graphrag_query.py "medications for hypertension" --patient=3
```

### Query with Custom Parameters

```bash
python3 src/query/fhir_graphrag_query.py \
  "chronic conditions" \
  --patient=3 \
  --top-k=10 \
  --vector-k=30 \
  --text-k=30 \
  --graph-k=10
```

**Parameters**:
- `--patient`: Filter results to specific patient ID
- `--top-k`: Number of final results (default: 10)
- `--vector-k`: Top K from vector search (default: 30)
- `--text-k`: Top K from text search (default: 30)
- `--graph-k`: Top K from graph traversal (default: 10)

---

## Demo Queries

Try these example queries to explore the knowledge graph:

### 1. Symptom-Based Query
```bash
python3 src/query/fhir_graphrag_query.py "Has the patient reported any respiratory symptoms?"
```

**What it demonstrates**: Vector search for symptom entities, graph traversal of CO_OCCURS_WITH relationships

### 2. Medication Query
```bash
python3 src/query/fhir_graphrag_query.py "What medications has the patient been prescribed?"
```

**What it demonstrates**: Entity type filtering (MEDICATION), TREATS relationships to conditions

### 3. Temporal Query
```bash
python3 src/query/fhir_graphrag_query.py "Timeline of patient's medical events"
```

**What it demonstrates**: Temporal entity extraction, PRECEDES relationships

### 4. Condition-Symptom Relationship
```bash
python3 src/query/fhir_graphrag_query.py "What conditions are associated with chest pain?"
```

**What it demonstrates**: Graph traversal (2-hop), CAUSES relationships

---

## Performance Benchmarks

### Expected Performance (51 DocumentReference dataset)

| Operation | Target | Typical |
|-----------|--------|---------|
| Entity extraction (per document) | < 2 sec | 4-5 sec (with LLM), 0.5 sec (regex-only) |
| Knowledge graph build (51 documents) | < 5 min | 3-4 min |
| Multi-modal query | < 1 sec | 0.8-0.9 sec |
| Graph traversal (2-hop) | < 500 ms | 200-300 ms |

### Monitoring Performance

View real-time performance metrics:

```bash
# View extraction metrics
python3 src/setup/fhir_graphrag_setup.py --mode=stats

# View query performance logs
tail -f logs/fhir_graphrag.log | grep "query_latency"
```

---

## Troubleshooting

### Issue: rag-templates library not found

**Error**: `ModuleNotFoundError: No module named 'iris_rag'`

**Solution**:
```bash
export PYTHONPATH="/Users/tdyar/ws/rag-templates:$PYTHONPATH"
# Or add to ~/.bashrc or ~/.zshrc for persistence
```

### Issue: IRIS connection failure

**Error**: `ConnectionRefusedError: [Errno 61] Connection refused`

**Solution**:
1. Verify IRIS container is running: `docker ps | grep iris-fhir`
2. Check port mapping: Should show `32782->1972/tcp`
3. Test connection: `telnet localhost 32782`
4. Restart container if needed: `docker restart iris-fhir`

### Issue: Low entity extraction accuracy

**Problem**: Many irrelevant or low-confidence entities extracted

**Solution**:
1. Increase confidence threshold in `config/fhir_graphrag_config.yaml`:
   ```yaml
   pipelines:
     graphrag:
       min_entity_confidence: 0.8  # Increase from 0.7
   ```
2. Enable LLM-based extraction (more accurate than regex-only)
3. Review sample entities and adjust regex patterns if needed

### Issue: Ollama LLM not available

**Error**: `ConnectionError: Failed to connect to Ollama at http://localhost:11434`

**Solution**:
1. Check Ollama status: `ollama list`
2. Start Ollama service: `ollama serve`
3. Or disable LLM and use regex-only:
   ```yaml
   llm:
     fallback_to_regex: true
   ```

### Issue: Knowledge graph build too slow

**Problem**: Build taking > 5 minutes for 51 documents

**Solution**:
1. Disable LLM and use regex-only (faster):
   ```yaml
   llm:
     provider: null  # Disable LLM
   ```
2. Increase batch size:
   ```yaml
   pipelines:
     graphrag:
       batch_size: 20  # Increase from 10
   ```
3. Enable parallel extraction:
   ```yaml
   pipelines:
     graphrag:
       parallel_extraction: true
       max_workers: 8  # Increase from 4
   ```

### Issue: Multi-modal query returns no results

**Problem**: Query returns empty results despite entities in knowledge graph

**Solution**:
1. Check patient filter is not too restrictive
2. Verify entities exist for query terms:
   ```sql
   SELECT * FROM RAG.Entities WHERE EntityText LIKE '%respiratory%';
   ```
3. Lower RRF threshold or increase top-k values
4. Check vector embeddings are populated

---

## Next Steps

### After Successful Setup

1. **Explore Entity Types**: Review extracted entities by type to understand medical concept coverage
2. **Analyze Relationships**: Examine entity relationships to validate medical accuracy
3. **Tune Parameters**: Adjust confidence thresholds, RRF weights, and top-k values based on results
4. **Extend Entity Types**: Add custom entity types for domain-specific concepts
5. **Benchmark Performance**: Profile extraction and query performance with larger datasets

### Advanced Usage

- **Custom Entity Extraction**: Modify `src/extractors/medical_entity_extractor.py` with domain-specific patterns
- **Relationship Rules**: Add custom relationship extraction rules for medical domain
- **Integration**: Integrate with existing `direct_fhir_vector_approach.py` for hybrid search
- **Visualization**: Build knowledge graph visualization using NetworkX or D3.js
- **Real-Time Updates**: Implement incremental entity extraction for new FHIR resources

---

## Additional Resources

### Documentation
- Full specification: `specs/001-fhir-graphrag/spec.md`
- Implementation plan: `specs/001-fhir-graphrag/plan.md`
- Data model: `specs/001-fhir-graphrag/data-model.md`
- Research findings: `specs/001-fhir-graphrag/research.md`

### Code References
- rag-templates GraphRAG pipeline: `/Users/tdyar/ws/rag-templates/iris_rag/pipelines/graphrag.py`
- BYOT specification: `/Users/tdyar/ws/rag-templates/specs/014-byot-as-described/spec.md`

### Support
- File issues: GitHub repository issues tracker
- Contact: Project maintainer

---

**Setup Status Checklist**:
- [ ] Python dependencies installed
- [ ] Configuration file created
- [ ] IRIS database connection verified
- [ ] Knowledge graph tables created
- [ ] Entities extracted (100+)
- [ ] Relationships identified (50+)
- [ ] Multi-modal query tested
- [ ] Performance benchmarks met

**Happy Querying!** 🎉
