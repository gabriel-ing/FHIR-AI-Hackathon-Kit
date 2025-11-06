# Data Model: FHIR GraphRAG Knowledge Graph

**Feature**: 001-fhir-graphrag
**Date**: 2025-11-06
**Status**: Design Phase

---

## Overview

This document defines the data models for the FHIR GraphRAG knowledge graph implementation, including entity schemas, relationship schemas, and state transitions. The design follows a zero-copy overlay approach where FHIR native tables remain unchanged and new knowledge graph tables (RAG.Entities, RAG.EntityRelationships) store extracted medical entities and their relationships.

---

## Entity Catalog

### 1. Medical Entity

**Purpose**: Represents a discrete medical concept extracted from clinical notes

**Attributes**:
- `EntityID` (BIGINT, PRIMARY KEY): Unique identifier for the entity
- `EntityText` (VARCHAR(500)): The text of the extracted entity (e.g., "chest pain", "aspirin")
- `EntityType` (VARCHAR(50)): Classification of entity type (see Entity Type Enumeration)
- `ResourceID` (BIGINT, FOREIGN KEY): Links to HSFHIR_X0001_R.Rsrc.ID (source FHIR resource)
- `Confidence` (FLOAT): Extraction confidence score (0.0-1.0)
- `EmbeddingVector` (VECTOR(DOUBLE, 384)): 384-dimensional embedding for vector search
- `ExtractedAt` (TIMESTAMP): When entity was extracted
- `ExtractedBy` (VARCHAR(100)): Extraction method ("regex", "llm", "hybrid")

**Relationships**:
- Many-to-One with FHIR Document (via ResourceID)
- Many-to-Many with other Medical Entities (via Entity Relationships)

**Validation Rules**:
- EntityText must not be empty
- EntityType must be one of valid types (enum)
- Confidence must be between 0.0 and 1.0
- ResourceID must reference existing FHIR resource
- EmbeddingVector must be exactly 384 dimensions

**Indexes**:
- PRIMARY KEY on EntityID
- FOREIGN KEY on ResourceID → HSFHIR_X0001_R.Rsrc(ID)
- INDEX on EntityType (for type-specific queries)
- INDEX on Confidence (for filtering low-confidence entities)
- VECTOR INDEX on EmbeddingVector (for similarity search)

---

### 2. Entity Relationship

**Purpose**: Represents a directed relationship between two medical entities

**Attributes**:
- `RelationshipID` (BIGINT, PRIMARY KEY): Unique identifier for the relationship
- `SourceEntityID` (BIGINT, FOREIGN KEY): ID of the source entity
- `TargetEntityID` (BIGINT, FOREIGN KEY): ID of the target entity
- `RelationshipType` (VARCHAR(50)): Type of relationship (see Relationship Type Enumeration)
- `ResourceID` (BIGINT, FOREIGN KEY): FHIR resource where relationship was identified
- `Confidence` (FLOAT): Relationship extraction confidence (0.0-1.0)
- `ExtractedAt` (TIMESTAMP): When relationship was extracted
- `Context` (VARCHAR(1000)): Text snippet showing relationship context

**Relationships**:
- Many-to-One with Medical Entity (SourceEntityID)
- Many-to-One with Medical Entity (TargetEntityID)
- Many-to-One with FHIR Document (via ResourceID)

**Validation Rules**:
- SourceEntityID and TargetEntityID must reference existing entities
- SourceEntityID ≠ TargetEntityID (no self-loops)
- RelationshipType must be one of valid types (enum)
- Confidence must be between 0.0 and 1.0
- ResourceID must reference existing FHIR resource

**Indexes**:
- PRIMARY KEY on RelationshipID
- FOREIGN KEY on SourceEntityID → RAG.Entities(EntityID)
- FOREIGN KEY on TargetEntityID → RAG.Entities(EntityID)
- FOREIGN KEY on ResourceID → HSFHIR_X0001_R.Rsrc(ID)
- INDEX on RelationshipType (for type-specific traversal)
- COMPOSITE INDEX on (SourceEntityID, RelationshipType) (for graph traversal)

---

### 3. FHIR Document (Existing)

**Purpose**: Represents a DocumentReference resource from FHIR native tables (read-only overlay)

**Attributes** (read-only, no modifications):
- `ID` (BIGINT, PRIMARY KEY): FHIR resource internal ID
- `ResourceString` (CLOB): FHIR JSON containing hex-encoded clinical notes
- `ResourceType` (VARCHAR(50)): FHIR resource type (always "DocumentReference" for our use case)
- `ResourceId` (VARCHAR(255)): FHIR resource identifier
- `Compartments` (VARCHAR(1000)): Patient compartment references (e.g., "Patient/3")
- `Deleted` (SMALLINT): Deletion flag (0 = active, 1 = deleted)

**Relationships**:
- One-to-Many with Medical Entity (via ResourceID foreign keys)
- One-to-Many with Entity Relationship (via ResourceID foreign keys)
- One-to-One with Vector Embeddings (via VectorSearch.FHIRResourceVectors)

**Access Pattern**: Read-only SELECT queries, no INSERT/UPDATE/DELETE

**Notes**:
- This table is part of FHIR native schema and must not be modified
- Clinical notes stored as hex-encoded data in ResourceString JSON
- Patient ID extracted from Compartments field using regex pattern `Patient/(\d+)`

---

### 4. Vector Embeddings (Existing)

**Purpose**: Stores 384-dimensional vector embeddings for FHIR DocumentReference resources (existing table, reused)

**Attributes** (existing schema, no modifications):
- `ResourceID` (BIGINT, FOREIGN KEY): Links to HSFHIR_X0001_R.Rsrc.ID
- `Vector` (VECTOR(DOUBLE, 384)): 384-dimensional embedding from all-MiniLM-L6-v2
- `ResourceType` (VARCHAR(50)): FHIR resource type
- `VectorModel` (VARCHAR(100)): Embedding model name
- `LastUpdated` (TIMESTAMP): When vector was generated

**Relationships**:
- Many-to-One with FHIR Document (via ResourceID)

**Access Pattern**: Read-only for multi-modal search (vector component)

**Notes**:
- This table was created by direct_fhir_vector_approach.py and must remain unchanged
- Reused for multi-modal search (vector search component)
- No new vectors generated (already have 51 DocumentReference vectors)

---

### 5. Knowledge Graph

**Purpose**: Aggregate structure of all entities and relationships forming a queryable medical knowledge network

**Composition**:
- Set of Medical Entities (nodes in graph)
- Set of Entity Relationships (directed edges in graph)
- Graph traversal algorithms (path finding, related entity discovery)

**Operations**:
- `TraverseRelationships(entityID, relationshipType, maxDepth)`: Find related entities
- `FindPath(sourceEntityID, targetEntityID, maxDepth)`: Find connection path
- `GetRelatedConcepts(query, topK, maxDepth)`: Discover related medical concepts
- `FilterByPatient(patientID)`: Limit graph to patient-specific entities

**Graph Properties**:
- Directed graph (relationships have source → target direction)
- May contain cycles (e.g., bidirectional CO_OCCURS_WITH relationships)
- Weighted edges (confidence scores)
- Attributed nodes (entity metadata)

**Storage**: No separate table - virtual graph constructed from RAG.Entities + RAG.EntityRelationships

---

### 6. Multi-Modal Search Result

**Purpose**: Represents the fusion of results from vector search, text search, and graph traversal

**Attributes** (in-memory, not persisted):
- `DocumentID`: FHIR resource ID
- `Content`: Clinical note text
- `VectorScore`: Similarity score from vector search (0.0-1.0)
- `TextScore`: Relevance score from text search (0.0-1.0)
- `GraphScore`: Importance score from graph traversal (0.0-1.0)
- `RRFScore`: Combined score from Reciprocal Rank Fusion
- `SourceMethods`: List of contributing search methods (["vector", "text", "graph"])
- `Entities`: List of matched/related medical entities
- `Relationships`: List of discovered entity relationships
- `Metadata`: FHIR resource metadata (patient ID, resource type, etc.)

**Ranking**: Results sorted by RRFScore descending

**RRF Score Calculation**:
```
RRF_score = Σ (1 / (k + rank_i))
where:
  k = 60 (RRF constant)
  rank_i = rank in search method i (1-based)
  sum over i in {vector, text, graph}
```

---

## Entity Type Enumeration

**Medical Entity Types** (configurable in YAML):

| Type | Description | Examples | Extraction Method |
|------|-------------|----------|-------------------|
| `SYMPTOM` | Patient-reported or observed symptoms | "cough", "fever", "chest pain", "nausea" | Regex + LLM |
| `CONDITION` | Medical conditions and diagnoses | "diabetes", "hypertension", "COPD", "asthma" | Regex + LLM |
| `MEDICATION` | Prescribed or administered medications | "aspirin", "metformin", "lisinopril", "ibuprofen" | Regex patterns (drug suffixes) |
| `PROCEDURE` | Medical procedures and tests | "blood test", "x-ray", "surgery", "MRI" | LLM primarily |
| `BODY_PART` | Anatomical locations | "chest", "lungs", "heart", "abdomen" | Regex + LLM |
| `TEMPORAL` | Time references and dates | "2023-01-15", "3 days ago", "last week" | Regex (date patterns) |

**Extensibility**: New entity types can be added by updating `pipelines:graphrag:entity_types` in YAML configuration

---

## Relationship Type Enumeration

**Entity Relationship Types** (configurable in YAML):

| Type | Description | Source → Target Example | Directionality |
|------|-------------|-------------------------|----------------|
| `TREATS` | Medication treats condition | aspirin TREATS headache | Directed |
| `CAUSES` | Condition causes symptom | diabetes CAUSES fatigue | Directed |
| `LOCATED_IN` | Symptom/condition located in body part | pain LOCATED_IN chest | Directed |
| `CO_OCCURS_WITH` | Symptoms/conditions appearing together | cough CO_OCCURS_WITH fever | Bidirectional |
| `PRECEDES` | Temporal ordering of events | symptom PRECEDES diagnosis | Directed |

**Extensibility**: New relationship types can be added by updating `pipelines:graphrag:relationship_types` in YAML configuration

**Bidirectional Handling**: For bidirectional relationships (e.g., CO_OCCURS_WITH), both directions are stored as separate rows:
- Entity A CO_OCCURS_WITH Entity B
- Entity B CO_OCCURS_WITH Entity A

---

## State Transitions

### Document Processing State Machine

```
┌─────────────────┐
│ FHIR Resource   │ (existing, unchanged)
│ in Rsrc table   │
└────────┬────────┘
         │
         │ 1. BYOT Adapter reads ResourceString
         ▼
┌─────────────────┐
│ FHIR JSON       │
│ (hex-encoded)   │
└────────┬────────┘
         │
         │ 2. Decode hex → UTF-8 text
         ▼
┌─────────────────┐
│ Clinical Note   │
│ (plain text)    │
└────────┬────────┘
         │
         │ 3. Convert to Document format
         ▼
┌─────────────────┐
│ rag-templates   │
│ Document object │
└────────┬────────┘
         │
         │ 4. Entity extraction (regex + LLM)
         ▼
┌─────────────────┐
│ Extracted       │
│ Entities (list) │
└────────┬────────┘
         │
         │ 5. Store in RAG.Entities
         ▼
┌─────────────────┐
│ Medical Entity  │
│ (persisted)     │
└────────┬────────┘
         │
         │ 6. Relationship extraction
         ▼
┌─────────────────┐
│ Entity          │
│ Relationships   │
└────────┬────────┘
         │
         │ 7. Store in RAG.EntityRelationships
         ▼
┌─────────────────┐
│ Knowledge Graph │
│ (queryable)     │
└─────────────────┘
```

**State Descriptions**:

1. **FHIR Resource**: DocumentReference exists in HSFHIR_X0001_R.Rsrc (unchanged)
2. **FHIR JSON**: ResourceString contains FHIR-compliant JSON with hex-encoded clinical note
3. **Clinical Note**: Decoded plain text clinical note ready for extraction
4. **Document**: rag-templates Document object with id, page_content, metadata
5. **Extracted Entities**: List of medical entities with types and confidence scores
6. **Medical Entity**: Persisted entity in RAG.Entities table with embeddings
7. **Entity Relationships**: Persisted relationships in RAG.EntityRelationships table
8. **Knowledge Graph**: Complete graph ready for multi-modal queries

**Idempotency**: Processing same FHIR resource multiple times:
- Check if ResourceID already exists in RAG.Entities
- If exists: Skip or update (configurable)
- If new: Process and store entities/relationships

---

## Data Flow Diagrams

### Setup Flow (Knowledge Graph Build)

```
User
  │
  │ run fhir_graphrag_setup.py
  ▼
┌─────────────────────────────────────────┐
│  Setup Script                           │
│  - Load BYOT config                     │
│  - Initialize GraphRAG pipeline         │
└────────────┬────────────────────────────┘
             │
             │ Load all DocumentReferences
             ▼
┌─────────────────────────────────────────┐
│  FHIR Document Adapter                  │
│  - Query HSFHIR_X0001_R.Rsrc            │
│  - Decode hex-encoded notes             │
│  - Convert to Document format           │
└────────────┬────────────────────────────┘
             │
             │ For each document
             ▼
┌─────────────────────────────────────────┐
│  GraphRAG Pipeline                      │
│  - Extract entities (regex + LLM)       │
│  - Extract relationships                │
│  - Generate embeddings                  │
└────────────┬────────────────────────────┘
             │
             │ Store entities and relationships
             ▼
┌─────────────────────────────────────────┐
│  IRIS Database                          │
│  - RAG.Entities ← insert entities       │
│  - RAG.EntityRelationships ← insert rels│
└─────────────────────────────────────────┘
```

### Query Flow (Multi-Modal Search)

```
User
  │
  │ Natural language query
  ▼
┌─────────────────────────────────────────┐
│  Query Interface                        │
│  - Parse query                          │
│  - Apply patient filter (optional)      │
└────────────┬────────────────────────────┘
             │
             │ Execute multi-modal search
             ├──────────┬──────────┬───────────┐
             │          │          │           │
             ▼          ▼          ▼           ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│  Vector  │ │  Text  │ │ Graph  │ │  Filter by  │
│  Search  │ │ Search │ │Traversal│ │  Patient    │
│ (top 30) │ │(top 30)│ │(top 10)│ │  (optional) │
└────┬─────┘ └───┬────┘ └───┬────┘ └──────┬──────┘
     │           │           │             │
     │           │           │             │
     └───────────┴───────────┴─────────────┘
                     │
                     │ Combine results
                     ▼
┌─────────────────────────────────────────┐
│  RRF Fusion                             │
│  - Calculate RRF scores                 │
│  - Merge results                        │
│  - Sort by combined score               │
└────────────┬────────────────────────────┘
             │
             │ Return ranked results
             ▼
┌─────────────────────────────────────────┐
│  Multi-Modal Search Result              │
│  - Ranked documents                     │
│  - Entities + relationships             │
│  - Source methods                       │
└─────────────────────────────────────────┘
```

---

## Data Constraints and Integrity

### Foreign Key Constraints

1. `RAG.Entities.ResourceID` → `HSFHIR_X0001_R.Rsrc.ID`
   - ON DELETE: CASCADE (if FHIR resource deleted, remove entities)
   - ON UPDATE: CASCADE

2. `RAG.EntityRelationships.SourceEntityID` → `RAG.Entities.EntityID`
   - ON DELETE: CASCADE (if entity deleted, remove its relationships)
   - ON UPDATE: CASCADE

3. `RAG.EntityRelationships.TargetEntityID` → `RAG.Entities.EntityID`
   - ON DELETE: CASCADE
   - ON UPDATE: CASCADE

4. `RAG.EntityRelationships.ResourceID` → `HSFHIR_X0001_R.Rsrc.ID`
   - ON DELETE: CASCADE
   - ON UPDATE: CASCADE

### Check Constraints

1. `RAG.Entities.Confidence CHECK (Confidence >= 0.0 AND Confidence <= 1.0)`
2. `RAG.Entities.EntityText CHECK (LENGTH(EntityText) > 0)`
3. `RAG.EntityRelationships.Confidence CHECK (Confidence >= 0.0 AND Confidence <= 1.0)`
4. `RAG.EntityRelationships CHECK (SourceEntityID != TargetEntityID)`

### Unique Constraints

1. Composite unique on `(EntityText, EntityType, ResourceID)` in RAG.Entities
   - Prevents duplicate extraction of same entity from same document
   - Allows same entity text across different resources or types

2. Composite unique on `(SourceEntityID, TargetEntityID, RelationshipType)` in RAG.EntityRelationships
   - Prevents duplicate relationships
   - Allows multiple relationship types between same entity pair

---

## Query Patterns

### Common Queries

**1. Get all entities for a patient**:
```sql
SELECT e.*
FROM RAG.Entities e
JOIN HSFHIR_X0001_R.Rsrc r ON e.ResourceID = r.ID
WHERE r.Compartments LIKE '%Patient/3%'
  AND e.Confidence >= 0.7
ORDER BY e.ExtractedAt DESC;
```

**2. Find relationships for a specific entity**:
```sql
SELECT
  s.EntityText AS Source,
  r.RelationshipType,
  t.EntityText AS Target,
  r.Confidence
FROM RAG.EntityRelationships r
JOIN RAG.Entities s ON r.SourceEntityID = s.EntityID
JOIN RAG.Entities t ON r.TargetEntityID = t.EntityID
WHERE s.EntityText = 'chest pain'
ORDER BY r.Confidence DESC;
```

**3. Graph traversal (2-hop relationships)**:
```sql
WITH RECURSIVE EntityGraph AS (
  -- Base case: Start entity
  SELECT EntityID, EntityText, 0 AS Depth
  FROM RAG.Entities
  WHERE EntityText = 'diabetes'

  UNION ALL

  -- Recursive case: Follow relationships
  SELECT e.EntityID, e.EntityText, eg.Depth + 1
  FROM EntityGraph eg
  JOIN RAG.EntityRelationships r ON eg.EntityID = r.SourceEntityID
  JOIN RAG.Entities e ON r.TargetEntityID = e.EntityID
  WHERE eg.Depth < 2
)
SELECT DISTINCT EntityID, EntityText, Depth
FROM EntityGraph
ORDER BY Depth, EntityText;
```

**4. Vector search with entity enrichment**:
```sql
SELECT
  r.ResourceString,
  e.EntityText,
  e.EntityType,
  VECTOR_COSINE(v.Vector, ?::VECTOR(DOUBLE, 384)) AS Similarity
FROM VectorSearch.FHIRResourceVectors v
JOIN HSFHIR_X0001_R.Rsrc r ON v.ResourceID = r.ID
LEFT JOIN RAG.Entities e ON r.ID = e.ResourceID
WHERE VECTOR_COSINE(v.Vector, ?::VECTOR(DOUBLE, 384)) > 0.7
ORDER BY Similarity DESC
LIMIT 30;
```

---

## Schema Evolution Strategy

### Versioning

- **Schema Version**: 1.0.0 (initial implementation)
- **Stored in**: RAG.SchemaVersion table (to be created)
- **Migration Strategy**: Alembic or custom migration scripts

### Backward Compatibility

- FHIR native tables (HSFHIR_X0001_R.Rsrc) must never be modified
- VectorSearch.FHIRResourceVectors must remain unchanged
- New columns added to RAG.* tables with DEFAULT values
- No breaking changes to existing columns

### Future Extensions

**Potential Schema Enhancements**:
1. Add `RAG.EntitySynonyms` table for entity normalization
2. Add `RAG.EntityProvenance` table for extraction source tracking
3. Add `RAG.QueryHistory` table for query performance analytics
4. Add `RAG.EntityFeedback` table for manual corrections/ratings
5. Add `RAG.TemporalRelationships` table for time-series analysis

---

**Status**: ✅ Data model design complete
**Next**: Create schema contracts (DDL SQL) in `contracts/` directory
