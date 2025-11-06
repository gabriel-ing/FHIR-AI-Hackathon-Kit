# Implementation Plan: FHIR GraphRAG Knowledge Graph

**Branch**: `001-fhir-graphrag` | **Date**: 2025-11-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-fhir-graphrag/spec.md`

## Summary

Implement GraphRAG knowledge graph capabilities on top of existing direct FHIR integration using rag-templates library with BYOT (Bring Your Own Table) overlay mode. The system will extract medical entities (SYMPTOM, CONDITION, MEDICATION, PROCEDURE, BODY_PART, TEMPORAL) and their relationships (TREATS, CAUSES, LOCATED_IN, CO_OCCURS_WITH, PRECEDES) from clinical notes in FHIR DocumentReference resources, enabling multi-modal search combining vector similarity, text matching, and graph traversal using Reciprocal Rank Fusion (RRF).

**Technical Approach**: Zero-copy overlay on existing FHIR native tables (HSFHIR_X0001_R.Rsrc) and vector table (VectorSearch.FHIRResourceVectors) with new knowledge graph tables (RAG.Entities, RAG.EntityRelationships). Uses rag-templates GraphRAG pipeline for entity extraction and multi-modal query execution.

## Technical Context

**Language/Version**: Python 3.12 (existing environment from direct_fhir_vector_approach.py)
**Primary Dependencies**:
- rag-templates (GraphRAG pipeline from /Users/tdyar/ws/rag-templates)
- iris-python-driver (IRIS database connector)
- sentence-transformers (all-MiniLM-L6-v2 model for 384-dim embeddings)
- PyYAML (configuration management)
- Ollama (optional LLM service for entity extraction)

**Storage**: InterSystems IRIS database (localhost:32782, namespace DEMO)
- Existing: HSFHIR_X0001_R.Rsrc (FHIR native table, read-only)
- Existing: VectorSearch.FHIRResourceVectors (companion vector table)
- New: RAG.Entities (medical entity storage)
- New: RAG.EntityRelationships (entity relationship storage)

**Testing**: pytest with integration tests for entity extraction, knowledge graph queries, and multi-modal search
**Target Platform**: macOS development environment (Darwin 24.5.0), deployable to Linux servers
**Project Type**: Single Python project (data science/analytics pipeline)
**Performance Goals**:
- Entity extraction: < 2 seconds per document
- Knowledge graph build: < 5 minutes for 51 documents
- Multi-modal queries: < 1 second response time

**Constraints**:
- Zero modifications to FHIR native schema (read-only overlay via BYOT)
- Maintain backward compatibility with direct_fhir_vector_approach.py
- Must use rag-templates library (no custom GraphRAG implementation)
- IRIS database at localhost:32782 (fixed development environment)

**Scale/Scope**:
- Initial dataset: 51 DocumentReference resources from 5 patients
- Expected entities: 100+ medical entities
- Expected relationships: 50+ entity relationships
- Target: Scalable to 1000+ documents with optimizations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Constitution template is empty (`.specify/memory/constitution.md` not yet populated). Proceeding with industry best practices for medical data processing:

### Assumed Principles (to be formalized in constitution)

1. **Data Integrity**: No modifications to source FHIR data (read-only overlay) ✅
2. **Backward Compatibility**: Existing implementations must continue functioning ✅
3. **Testability**: All entity extraction and query logic must be independently testable ✅
4. **Performance**: Sub-second query response times for acceptable user experience ✅
5. **Error Handling**: Graceful degradation when optional services (LLM) unavailable ✅
6. **Configuration Management**: External YAML configuration for environment-specific settings ✅

### Constitution Violations

None - all assumed principles are satisfied by the design.

## Project Structure

### Documentation (this feature)

```text
specs/001-fhir-graphrag/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - rag-templates BYOT research
├── data-model.md        # Phase 1 output - Entity/Relationship schema
├── quickstart.md        # Phase 1 output - Setup and usage guide
├── contracts/           # Phase 1 output - API/schema contracts
│   ├── byot-config-schema.yaml    # BYOT configuration contract
│   ├── entity-schema.json         # RAG.Entities table schema
│   └── relationship-schema.json   # RAG.EntityRelationships table schema
├── checklists/
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
# Single Python project structure (data science/analytics)
config/
└── fhir_graphrag_config.yaml      # BYOT configuration for rag-templates

src/
├── adapters/
│   └── fhir_document_adapter.py   # FHIR JSON → rag-templates Document
├── extractors/
│   └── medical_entity_extractor.py # Regex + LLM entity extraction
├── setup/
│   └── fhir_graphrag_setup.py     # Pipeline initialization script
└── query/
    └── fhir_graphrag_query.py     # Multi-modal query interface

tests/
├── integration/
│   ├── test_byot_overlay.py       # BYOT FHIR table access
│   ├── test_entity_extraction.py  # End-to-end entity extraction
│   └── test_multimodal_search.py  # Vector + Text + Graph fusion
├── unit/
│   ├── test_fhir_adapter.py       # Document adapter logic
│   ├── test_entity_extractor.py   # Pattern matching and LLM extraction
│   └── test_rrf_fusion.py         # RRF ranking algorithm
└── fixtures/
    ├── sample_fhir_resources.json # Test FHIR DocumentReferences
    └── expected_entities.json     # Expected extraction results

# Existing files (preserved for backward compatibility)
direct_fhir_vector_approach.py     # Existing POC - must remain functional
Tutorial/
└── Utils/
    └── get_iris_connection.py     # Shared connection utility
```

**Structure Decision**: Single Python project structure is appropriate because:
- No frontend/backend separation (backend-only data pipeline)
- No mobile/web application components
- Focused on data processing and query execution
- Integrates with existing tutorial code structure
- All components share same Python environment and dependencies

## Architecture

### System Components

```text
┌─────────────────────────────────────────────────────────────────┐
│                     FHIR AI Hackathon System                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────┐
        │     IRIS Database (localhost:32782)       │
        │              Namespace: DEMO              │
        └───────────────────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ▼                                               ▼
┌──────────────────────┐                    ┌──────────────────────┐
│  FHIR Native Tables  │                    │   Vector Storage     │
│  (READ-ONLY)         │                    │   (EXISTING)         │
├──────────────────────┤                    ├──────────────────────┤
│ HSFHIR_X0001_R.Rsrc  │                    │ VectorSearch.        │
│ - ResourceString     │                    │ FHIRResourceVectors  │
│ - ResourceType       │                    │ - ResourceID         │
│ - ResourceId         │                    │ - Vector (384 dim)   │
│ - Compartments       │                    │ - VectorModel        │
│ - Deleted            │                    │ - LastUpdated        │
└──────────────────────┘                    └──────────────────────┘
        │                                               │
        │                                               │
        └───────────────────┬───────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │   BYOT Adapter Layer          │
            │   (fhir_document_adapter.py)  │
            ├───────────────────────────────┤
            │ - Decode hex-encoded notes    │
            │ - Extract patient ID          │
            │ - Convert to Document format  │
            └───────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │   rag-templates Pipeline      │
            │   (GraphRAG from external)    │
            ├───────────────────────────────┤
            │ - Entity extraction (DSPy)    │
            │ - Relationship mapping        │
            │ - Connection pooling          │
            │ - Multi-modal search (RRF)    │
            └───────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌──────────────────────┐            ┌──────────────────────┐
│ Knowledge Graph      │            │  Query Interface     │
│ Tables (NEW)         │            │  (NEW)               │
├──────────────────────┤            ├──────────────────────┤
│ RAG.Entities         │            │ Multi-Modal Search   │
│ - EntityID           │◄───────────┤ - Vector Search      │
│ - EntityText         │            │ - Text Search        │
│ - EntityType         │            │ - Graph Traversal    │
│ - ResourceID (FK)    │            │ - RRF Fusion         │
│ - Confidence         │            └──────────────────────┘
│ - EmbeddingVector    │
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│ RAG.Entity           │
│ Relationships (NEW)  │
├──────────────────────┤
│ - SourceEntityID     │
│ - TargetEntityID     │
│ - RelationshipType   │
│ - ResourceID (FK)    │
│ - Confidence         │
└──────────────────────┘
```

### Data Flow

**Setup Flow (Knowledge Graph Build)**:
1. `fhir_graphrag_setup.py` loads BYOT configuration from `config/fhir_graphrag_config.yaml`
2. Connects to IRIS database and queries `HSFHIR_X0001_R.Rsrc` for DocumentReference resources
3. `FHIRDocumentAdapter` decodes hex-encoded clinical notes from FHIR JSON
4. Converts FHIR resources to rag-templates `Document` format
5. rag-templates GraphRAG pipeline extracts entities using `MedicalEntityExtractor`
6. Entities stored in `RAG.Entities` table with confidence scores
7. Relationships extracted and stored in `RAG.EntityRelationships` table
8. Process repeats for all 51 DocumentReference resources

**Query Flow (Multi-Modal Search)**:
1. User submits natural language query via `fhir_graphrag_query.py`
2. Query interface initializes rag-templates GraphRAG pipeline
3. **Vector Search**: Query embedded and compared to entity embeddings (top 30)
4. **Text Search**: Keyword matching on entity text and clinical notes (top 30)
5. **Graph Traversal**: Related entities discovered through relationships (top 10)
6. **RRF Fusion**: Results combined using Reciprocal Rank Fusion algorithm
7. Final ranked results with entities, relationships, and source documents returned
8. Optional: Patient-specific filtering applied via Compartments field

### Integration Points

**External Dependencies**:
- **rag-templates library** (`/Users/tdyar/ws/rag-templates`): Core GraphRAG pipeline
  - Integration: Python path import, configuration via YAML
  - Contract: BYOT mode with custom table mapping
  - Fallback: None (required dependency)

- **IRIS Database** (`localhost:32782`): Data storage and vector search
  - Integration: iris-python-driver, connection pooling from rag-templates
  - Contract: SQL queries, table schemas
  - Fallback: Fail fast with clear error message

- **sentence-transformers** (existing): Embedding generation
  - Integration: Model `all-MiniLM-L6-v2` for 384-dim vectors
  - Contract: Consistent with existing VectorSearch.FHIRResourceVectors
  - Fallback: None (already installed)

- **Ollama** (optional): LLM-based entity extraction
  - Integration: REST API for enhanced extraction beyond regex
  - Contract: Prompt templates for medical entity recognition
  - Fallback: Regex-based pattern matching only

**Internal Dependencies**:
- **direct_fhir_vector_approach.py** (existing POC): Must remain functional
  - Integration: Shared IRIS connection utilities, VectorSearch tables
  - Contract: No modifications to VectorSearch.FHIRResourceVectors schema
  - Compatibility: Tested via integration tests

- **Tutorial/Utils/get_iris_connection.py** (existing): Database connection helper
  - Integration: Shared connection logic for consistency
  - Contract: Returns IRIS connection object
  - Enhancement: May need pooling wrapper from rag-templates

## Technology Stack Decisions

### Primary Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Language | Python | 3.12 | Existing project standard, data science ecosystem |
| Database | InterSystems IRIS | Latest | Existing FHIR server, native vector support |
| GraphRAG Framework | rag-templates | Latest | Production-hardened, BYOT support, medical entities |
| Embeddings | sentence-transformers | Latest | Existing model (all-MiniLM-L6-v2), 384-dim vectors |
| Configuration | PyYAML | Latest | Standard Python config format, rag-templates compatible |
| Testing | pytest | Latest | Python testing standard, existing framework |

### Supporting Technologies

| Component | Technology | Purpose | Optional |
|-----------|-----------|---------|----------|
| LLM Service | Ollama | Enhanced entity extraction | Yes - fallback to regex |
| Connection Pooling | rag-templates built-in | Efficient database connections | No |
| Entity Extraction | DSPy (via rag-templates) | Medical entity recognition | No |
| Result Fusion | RRF algorithm (rag-templates) | Multi-modal search ranking | No |
| Logging | Python logging | Monitoring and debugging | No |

### Alternatives Considered

**GraphRAG Implementation**:
- ❌ Custom GraphRAG from scratch: Too time-consuming, reinventing wheel
- ❌ Neo4j graph database: Requires data migration, breaks zero-copy constraint
- ✅ rag-templates with BYOT: Zero-copy, production-ready, medical focus

**Entity Extraction**:
- ❌ Rule-based only: Lower accuracy, no learning from context
- ❌ Fine-tuned medical NER model: Training overhead, deployment complexity
- ✅ Hybrid (regex + LLM via rag-templates): Balance accuracy and practicality

**Vector Storage**:
- ❌ Separate vector database (Pinecone, Weaviate): Data duplication, sync complexity
- ❌ Regenerate embeddings in new format: Breaks compatibility, wasted computation
- ✅ Reuse existing VectorSearch.FHIRResourceVectors: Zero waste, compatibility

## Phases

### Phase 0: Research & Discovery ✅

**Objective**: Resolve all NEEDS CLARIFICATION items and validate rag-templates BYOT capability

**Research Tasks**:
1. Verify rag-templates BYOT mode supports IRIS FHIR table structure
2. Identify exact BYOT configuration schema for custom table mapping
3. Determine medical entity types supported by rag-templates (confirm SYMPTOM, CONDITION, etc.)
4. Validate RRF fusion algorithm parameters (vector_k, text_k, graph_k weights)
5. Confirm rag-templates entity extraction performance (< 2 sec/doc feasibility)

**Output**: `research.md` with decisions, rationale, and alternatives

### Phase 1: Design & Contracts

**Objective**: Define data models, API contracts, and setup procedures

**Deliverables**:

1. **data-model.md**: Entity and relationship schemas
   - RAG.Entities table schema (EntityID, EntityText, EntityType, ResourceID, Confidence, EmbeddingVector)
   - RAG.EntityRelationships table schema (SourceEntityID, TargetEntityID, RelationshipType, ResourceID, Confidence)
   - Entity type enumeration (SYMPTOM, CONDITION, MEDICATION, PROCEDURE, BODY_PART, TEMPORAL)
   - Relationship type enumeration (TREATS, CAUSES, LOCATED_IN, CO_OCCURS_WITH, PRECEDES)
   - State transitions: FHIR Resource → Document → Entities → Relationships

2. **contracts/**: Schema and configuration contracts
   - `byot-config-schema.yaml`: BYOT configuration structure for rag-templates
   - `entity-schema.json`: RAG.Entities table DDL and constraints
   - `relationship-schema.json`: RAG.EntityRelationships table DDL and constraints

3. **quickstart.md**: Setup and usage guide
   - Prerequisites (rag-templates installation, IRIS credentials, Python environment)
   - Knowledge graph build steps (run fhir_graphrag_setup.py)
   - Query examples (multi-modal search with patient filtering)
   - Performance benchmarks (expected timings)
   - Troubleshooting (missing library, connection failures, low confidence entities)

**Agent Context Update**:
- Run `.specify/scripts/bash/update-agent-context.sh claude`
- Add rag-templates GraphRAG pipeline patterns
- Add BYOT configuration conventions
- Add medical entity extraction patterns
- Preserve existing FHIR/IRIS knowledge

### Phase 2: Implementation Tasks

**Objective**: Generate actionable, dependency-ordered task list

**Output**: `tasks.md` (created by `/speckit.tasks` command, not by this command)

**Task Categories** (preview):
1. **Foundation**: BYOT configuration, table creation, FHIR adapter
2. **Entity Extraction**: Medical entity extractor, rag-templates integration
3. **Knowledge Graph**: Entity/relationship storage, graph population
4. **Multi-Modal Search**: Query interface, RRF fusion, patient filtering
5. **Testing**: Unit tests, integration tests, performance benchmarks
6. **Documentation**: Setup guide, API documentation, troubleshooting

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| rag-templates BYOT incompatible with IRIS | High | Low | Phase 0 research validates BYOT, fallback to direct SQL if needed |
| Entity extraction accuracy < 80% | Medium | Medium | Hybrid approach (regex + LLM), confidence thresholds, manual review sample |
| Performance targets missed (> 2 sec/doc) | Medium | Low | Profiling, batch optimization, async processing |
| FHIR schema changes break overlay | High | Very Low | Read-only access, schema version checks, error handling |
| rag-templates library not at expected path | High | Medium | Configuration parameter, installation guide, clear error messages |
| Concurrent writes to knowledge graph | Medium | Low | Single-threaded setup script, database constraints, transaction management |
| LLM service (Ollama) unavailable | Low | Medium | Graceful fallback to regex patterns, documented limitation |
| Backward compatibility broken | High | Low | Integration tests for direct_fhir_vector_approach.py, CI checks |

## Performance Optimization Strategy

**Entity Extraction Optimization**:
- Batch processing of DocumentReference resources (10 at a time)
- Parallel entity extraction using multiprocessing pool
- Caching of compiled regex patterns
- LLM request batching (if Ollama available)

**Query Optimization**:
- Connection pooling from rag-templates (reuse connections)
- Prepared statement caching for FHIR table queries
- Vector index hints for IRIS (VECTOR_COSINE optimization)
- Result pagination to limit initial load

**Knowledge Graph Build Optimization**:
- Incremental processing (skip already-processed documents)
- Checkpoint/resume capability for large datasets
- Bulk insert for entities and relationships
- Indexing strategy (EntityType, RelationshipType, ResourceID)

## Monitoring & Observability

**Metrics to Track**:
- Entity extraction performance (avg time per document)
- Entity extraction accuracy (precision/recall on sample)
- Knowledge graph size (entity count, relationship count)
- Query performance (p50, p95, p99 latencies)
- Multi-modal search contribution (% results from vector vs. text vs. graph)
- Error rates (connection failures, malformed FHIR, extraction errors)

**Logging Strategy**:
- Structured JSON logging for machine parsing
- Log levels: DEBUG (entity extraction details), INFO (progress), ERROR (failures)
- Log rotation for long-running processes
- Integration with existing Tutorial logging patterns

## Next Steps

**Completed Actions**:
1. ✅ Specification complete (`spec.md`)
2. ✅ Implementation plan complete (this file)
3. ✅ Phase 0: Research rag-templates BYOT (`research.md` created)
4. ✅ Phase 1: Design contracts (`data-model.md`, `contracts/`, `quickstart.md` created)

**Remaining Actions**:
5. ⏳ Phase 2: Generate tasks (`/speckit.tasks` command - user must run separately)

**Command Execution**:
- ✅ `/speckit.plan` (this command) - **COMPLETE**
- ⏳ User runs `/speckit.tasks` to generate implementation task list

---

## Phase 0 & 1 Deliverables Summary

### Phase 0: Research (Complete)
- ✅ `research.md` - Comprehensive rag-templates BYOT validation
- ✅ All 6 research questions resolved
- ✅ Technology stack validated
- ✅ Configuration schema documented

### Phase 1: Design & Contracts (Complete)
- ✅ `data-model.md` - Complete entity and relationship schemas
- ✅ `contracts/byot-config-schema.yaml` - Full YAML configuration template
- ✅ `contracts/entity-schema.json` - RAG.Entities table DDL and constraints
- ✅ `contracts/relationship-schema.json` - RAG.EntityRelationships table DDL
- ✅ `quickstart.md` - Setup and usage guide with troubleshooting

---

**Status**: Planning complete. Ready for task generation with `/speckit.tasks`
