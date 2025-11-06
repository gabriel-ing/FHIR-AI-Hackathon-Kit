# FHIR GraphRAG Query Examples

## Quick Start

The implementation provides two query interfaces:

1. **Full Multi-Modal** (`fhir_graphrag_query.py`): Vector + Text + Graph search
2. **Fast Query** (`fhir_simple_query.py`): Text + Graph search (4x faster)

## Example Queries

### Example 1: Symptom-Based Search

**Query**: "chest pain"

**Full Multi-Modal Search**:
```bash
python3 src/query/fhir_graphrag_query.py "chest pain" --top-k 3
```

**Results**:
- Vector: 30 semantic matches
- Text: 23 keyword matches
- Graph: 9 entity matches
- **Time**: 0.242 seconds

**Fast Query**:
```bash
python3 src/query/fhir_simple_query.py "chest pain" --top-k 3
```

**Results**:
- Text: 23 keyword matches
- Graph: 9 entity matches
- **Time**: 0.063 seconds (4x faster)

### Example 2: Respiratory Conditions

**Query**: "respiratory symptoms breathing difficulty"

**Command**:
```bash
python3 src/query/fhir_graphrag_query.py "respiratory symptoms breathing difficulty" --top-k 5
```

**Top Result** (Document 1477):
- **RRF Score**: 0.0492
  - Vector: 0.0164 (semantic similarity to respiratory issues)
  - Text: 0.0164 (keywords: respiratory, symptoms, breathing, difficulty)
  - Graph: 0.0164 (entity: "difficulty breathing" as SYMPTOM)
- **Entities**: fever (0.95), difficulty breathing (0.95), cough (0.90), bronchitis (0.90)
- **Clinical note**: "Aurora was brought in with a 3-day history of persistent cough and difficulty breathing..."
- **Time**: 0.468 seconds

### Example 3: Chronic Conditions

**Query**: "hypertension diabetes"

**Fast Query**:
```bash
python3 src/query/fhir_simple_query.py "hypertension diabetes" --top-k 2
```

**Results**:
- **Document 2849**: Perfect match with both conditions
  - Entities: hypertension (CONDITION, 1.00), diabetes (CONDITION, 1.00)
  - Also shows: chest pain, shortness of breath (co-occurring symptoms)
- **Time**: 0.004 seconds

### Example 4: Patient-Specific Search

**Query**: Find all respiratory issues for patient 5

**Command**:
```bash
python3 src/query/fhir_graphrag_query.py "respiratory breathing cough" --patient 5 --top-k 5
```

**Behavior**:
- Filters all searches to patient 5 only
- Returns respiratory-related documents for that patient
- Maintains multi-modal search (vector + text + graph)

### Example 5: Medication Search

**Query**: "aspirin ibuprofen medications"

**Fast Query**:
```bash
python3 src/query/fhir_simple_query.py "aspirin ibuprofen" --top-k 5
```

**Expected Results**:
- Documents mentioning these medications
- Entity matches: aspirin (MEDICATION), ibuprofen (MEDICATION)
- Related conditions they treat via knowledge graph

## Query Parameters

### Common Parameters

Both query interfaces support:

- `query`: Search query text (required)
- `--top-k`: Number of final results (default: 5)
- `--patient`: Filter by patient ID
- `--config`: Custom config file path

### Full Multi-Modal Only

`fhir_graphrag_query.py` additional parameters:

- `--vector-k`: Number of vector results (default: 30)
- `--text-k`: Number of text results (default: 30)
- `--graph-k`: Number of graph results (default: 10)
- `--no-vector`: Disable vector search (use text + graph only)

### Fast Query Only

`fhir_simple_query.py` additional parameters:

- `--text-k`: Number of text results (default: 30)
- `--graph-k`: Number of graph results (default: 10)

## Performance Comparison

| Query Type | Vector | Text | Graph | Time | Best For |
|------------|--------|------|-------|------|----------|
| **Full Multi-Modal** | ✅ | ✅ | ✅ | 0.242s | Best relevance ranking |
| **Fast Query** | ❌ | ✅ | ✅ | 0.063s | High throughput |

## Understanding Results

### RRF Score

Results are ranked by **RRF (Reciprocal Rank Fusion) score**:
- Higher score = better match
- Combines rankings from all search methods
- Formula: `score = sum(1 / (60 + rank))` across search modalities

### Score Breakdown

Each result shows contribution from each search method:

```
RRF Score: 0.0481
  - Vector (semantic): 0.0164
  - Text (keywords):   0.0159
  - Graph (entities):  0.0159
```

**Interpretation**:
- **High vector score**: Semantically similar (even with different words)
- **High text score**: Contains exact keywords
- **High graph score**: Matches important medical entities/concepts

### Entity Information

Results display extracted medical entities:

```
Entities extracted (14):
  - hypertension (CONDITION, conf=1.00)
  - diabetes (CONDITION, conf=1.00)
  - chest pain (SYMPTOM, conf=0.95)
  - shortness of breath (SYMPTOM, conf=0.95)
```

**Entity Types**:
- **SYMPTOM**: Patient symptoms (chest pain, fever, cough)
- **CONDITION**: Diagnosed conditions (hypertension, diabetes)
- **MEDICATION**: Treatments (aspirin, ibuprofen)
- **PROCEDURE**: Medical procedures (CT scan, blood test)
- **BODY_PART**: Anatomical locations (chest, abdomen)
- **TEMPORAL**: Dates and times (2024-11-21, 3 days ago)

### Relationships

Results may show entity relationships:

```
Relationships (2):
  - CHEST PAIN (SYMPTOM) --[CO_OCCURS_WITH]--> SHORTNESS OF BREATH (SYMPTOM)
  - NAUSEA (SYMPTOM) --[CO_OCCURS_WITH]--> VOMITING (SYMPTOM)
```

**Relationship Types**:
- **CO_OCCURS_WITH**: Symptoms/conditions that appear together
- **TREATS**: Medications that treat conditions (future enhancement)
- **CAUSES**: Conditions that cause symptoms (future enhancement)
- **LOCATED_IN**: Symptoms in body parts (future enhancement)

## Use Cases

### Clinical Decision Support

**Scenario**: Doctor wants to find similar cases

```bash
python3 src/query/fhir_graphrag_query.py "persistent cough fever fatigue" --top-k 10
```

**Benefit**: Multi-modal search finds:
- Exact keyword matches (text search)
- Semantically similar cases (vector search)
- Cases with same medical entities (graph search)

### Population Health

**Scenario**: Find all patients with specific conditions

```bash
python3 src/query/fhir_simple_query.py "diabetes hypertension" --top-k 100
```

**Benefit**: Fast query (0.004s) enables:
- Real-time population queries
- Batch processing of patient records
- Quality metrics calculation

### Medical Research

**Scenario**: Find documents mentioning specific symptoms

```bash
python3 src/query/fhir_graphrag_query.py "respiratory symptoms dyspnea" --top-k 50
```

**Benefit**: Comprehensive search finds:
- Exact symptom mentions (text)
- Related conditions (vector similarity)
- Entity relationships (graph traversal)

## Advanced Usage

### Combining with Filters

**Find recent respiratory cases for patient 3**:
```bash
python3 src/query/fhir_graphrag_query.py "respiratory breathing" --patient 3 --top-k 10
```

### Adjusting Search Depth

**Deep search with more candidates**:
```bash
python3 src/query/fhir_graphrag_query.py "chest pain" --vector-k 50 --text-k 50 --graph-k 20 --top-k 10
```

### Fast Batch Queries

**Process multiple queries quickly**:
```bash
for query in "chest pain" "fever" "hypertension"; do
  python3 src/query/fhir_simple_query.py "$query" --top-k 5
done
```

## Tips

### When to Use Full Multi-Modal
- ✅ Need best possible relevance ranking
- ✅ Semantic understanding important
- ✅ Small to medium result sets (< 50 documents)
- ✅ Interactive queries (< 500ms acceptable)

### When to Use Fast Query
- ✅ Need sub-100ms response time
- ✅ High-throughput batch processing
- ✅ Large result sets (100+ documents)
- ✅ Keyword matching sufficient

## Troubleshooting

### No Results Found

**Possible causes**:
1. No documents match query terms
2. Knowledge graph not built: Run `python3 src/setup/fhir_graphrag_setup.py --mode=build`
3. Typo in query text

**Fix**: Try broader terms or check knowledge graph status:
```bash
python3 src/setup/fhir_graphrag_setup.py --mode=stats
```

### Slow Queries

**Possible causes**:
1. PyTorch/vector encoding overhead
2. Too many candidates (vector-k, text-k, graph-k too high)

**Fix**: Use fast query or reduce candidate counts:
```bash
python3 src/query/fhir_simple_query.py "query" --top-k 5
# OR
python3 src/query/fhir_graphrag_query.py "query" --vector-k 10 --text-k 10 --graph-k 5
```

### PyTorch Errors

**Error**: SentenceTransformer segfault

**Fix**: PyTorch version issue, try:
```bash
# Use fast query instead (no PyTorch needed)
python3 src/query/fhir_simple_query.py "query" --top-k 5

# OR use --no-vector flag
python3 src/query/fhir_graphrag_query.py "query" --no-vector --top-k 5
```

## Summary

**Quick Comparison**:

| Feature | Full Multi-Modal | Fast Query |
|---------|-----------------|------------|
| **Command** | `fhir_graphrag_query.py` | `fhir_simple_query.py` |
| **Search Methods** | Vector + Text + Graph | Text + Graph |
| **Performance** | 0.242 - 0.468s | 0.004 - 0.063s |
| **Best For** | Best relevance | High throughput |
| **Dependencies** | PyTorch, SentenceTransformer | None (IRIS + Python stdlib) |

Both interfaces support the same query syntax and return results in the same format!
