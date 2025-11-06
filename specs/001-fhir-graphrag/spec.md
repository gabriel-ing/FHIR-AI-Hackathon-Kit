# Feature Specification: FHIR GraphRAG Knowledge Graph

**Feature Branch**: `001-fhir-graphrag`
**Created**: 2025-11-05
**Status**: Draft
**Input**: User description: "Implement GraphRAG knowledge graph capabilities on top of existing direct FHIR integration"

## Overview

This feature adds knowledge graph capabilities to the existing direct FHIR integration by implementing GraphRAG (Graph-based Retrieval Augmented Generation) using the rag-templates library. The implementation uses a zero-copy BYOT (Bring Your Own Table) overlay approach that reads directly from existing FHIR native tables without requiring data migration or schema modifications.

### Context

The system currently has:
- Working proof-of-concept in `direct_fhir_vector_approach.py` that bypasses SQL Builder
- Direct access to FHIR native tables (`HSFHIR_X0001_R.Rsrc`)
- Companion vector table (`VectorSearch.FHIRResourceVectors`) with 51 DocumentReference resources
- 384-dimensional vectors from all-MiniLM-L6-v2 model
- IRIS database at localhost:32782, namespace DEMO

### Goal

Enhance the existing vector search capability with knowledge graph extraction and multi-modal search that combines vector similarity, text search, and graph traversal to provide richer medical insights from clinical notes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Medical Knowledge Graph (Priority: P1)

A medical researcher needs to automatically extract structured medical knowledge (symptoms, conditions, medications, procedures) from unstructured clinical notes to enable relationship-based queries.

**Why this priority**: This is the foundation for all knowledge graph capabilities. Without entity extraction and relationship mapping, multi-modal search cannot function. It delivers immediate value by structuring previously unstructured clinical data.

**Independent Test**: Can be fully tested by running the setup script on the 51 existing DocumentReference resources and verifying that medical entities are extracted and stored in the knowledge graph tables. Delivers value by making implicit medical relationships explicit and queryable.

**Acceptance Scenarios**:

1. **Given** 51 DocumentReference resources exist in FHIR native tables, **When** the GraphRAG setup script is executed, **Then** medical entities are extracted and stored in RAG.Entities table with entity types (SYMPTOM, CONDITION, MEDICATION, PROCEDURE, BODY_PART, TEMPORAL)
2. **Given** clinical notes contain medical relationships (e.g., "prescribed aspirin for chest pain"), **When** entity extraction completes, **Then** relationships are identified and stored in RAG.EntityRelationships table with relationship types (TREATS, CAUSES, LOCATED_IN, CO_OCCURS_WITH, PRECEDES)
3. **Given** entity extraction is complete, **When** querying the knowledge graph tables, **Then** each entity has a confidence score indicating extraction certainty
4. **Given** the BYOT configuration is active, **When** new DocumentReferences are added to FHIR tables, **Then** entities can be extracted from new documents without modifying the FHIR schema

---

### User Story 2 - Multi-Modal Medical Search (Priority: P2)

A clinician needs to query patient medical history using natural language and receive results that combine semantic similarity, keyword matching, and medical relationship traversal for comprehensive answers.

**Why this priority**: This delivers the primary user-facing value of the knowledge graph - better search results through multi-modal fusion. Depends on P1 being complete but provides the key differentiation from basic vector search.

**Independent Test**: Can be tested independently by running predefined medical queries (e.g., "respiratory symptoms", "medications for hypertension") and verifying that results include vector-matched documents, text-matched keywords, and graph-traversed related entities. Delivers value through more accurate and comprehensive search results.

**Acceptance Scenarios**:

1. **Given** the knowledge graph is populated, **When** a user queries "respiratory symptoms", **Then** results include documents matching via vector similarity, text keyword matching, and graph traversal of symptom relationships
2. **Given** a patient-specific filter is applied, **When** executing a multi-modal query, **Then** only entities and documents for that patient are returned
3. **Given** multiple search methods return overlapping results, **When** results are combined using RRF (Reciprocal Rank Fusion), **Then** the final ranking balances contributions from vector, text, and graph search
4. **Given** a query about medication-condition relationships, **When** graph traversal is enabled, **Then** related entities are discovered through TREATS relationships even if not directly mentioned in the query

---

### User Story 3 - Performance-Optimized Knowledge Graph Queries (Priority: P3)

System administrators need to ensure that knowledge graph queries complete within acceptable time limits while supporting concurrent users and maintaining data consistency.

**Why this priority**: Performance optimization is important for production use but can be refined after core functionality (P1, P2) is working. Initial implementation may have acceptable performance for the small dataset (51 documents), with optimization needed as data grows.

**Independent Test**: Can be tested by running performance benchmarks on entity extraction, knowledge graph build, and query execution times. Delivers value by ensuring the system scales to production workloads.

**Acceptance Scenarios**:

1. **Given** a single DocumentReference resource, **When** entity extraction is performed, **Then** processing completes in under 2 seconds
2. **Given** all 51 DocumentReference resources need processing, **When** the knowledge graph build is initiated, **Then** complete processing finishes in under 5 minutes
3. **Given** the knowledge graph is populated, **When** a multi-modal query is executed, **Then** results are returned in under 1 second
4. **Given** the rag-templates library provides connection pooling, **When** multiple concurrent queries are executed, **Then** database connections are efficiently managed without exhaustion

---

### Edge Cases

- What happens when a clinical note contains no extractable medical entities (empty/administrative notes)?
- How does the system handle ambiguous entity types (e.g., "cold" as symptom vs. temperature)?
- What occurs when entity extraction confidence is below acceptable thresholds?
- How are duplicate entities across multiple documents deduplicated in the knowledge graph?
- What happens when FHIR native tables contain non-DocumentReference resources?
- How does the system handle malformed FHIR JSON in ResourceString fields?
- What occurs when the rag-templates library is not found at the expected path?
- How are entity relationships resolved when temporal ordering is ambiguous?
- What happens when vector embeddings already exist but knowledge graph tables are empty?
- How does the system handle concurrent writes to knowledge graph tables during entity extraction?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read FHIR DocumentReference resources from native FHIR tables (HSFHIR_X0001_R.Rsrc) without copying or migrating data
- **FR-002**: System MUST decode hex-encoded clinical notes from FHIR JSON ResourceString fields
- **FR-003**: System MUST extract medical entities from clinical notes and classify them into types: SYMPTOM, CONDITION, MEDICATION, PROCEDURE, BODY_PART, TEMPORAL
- **FR-004**: System MUST identify relationships between extracted entities and classify them into types: TREATS, CAUSES, LOCATED_IN, CO_OCCURS_WITH, PRECEDES
- **FR-005**: System MUST store extracted entities in RAG.Entities table with fields: EntityID, EntityText, EntityType, ResourceID (linking to FHIR native table), Confidence, EmbeddingVector
- **FR-006**: System MUST store entity relationships in RAG.EntityRelationships table with fields: SourceEntityID, TargetEntityID, RelationshipType, ResourceID, Confidence
- **FR-007**: System MUST preserve existing VectorSearch.FHIRResourceVectors table and maintain compatibility with direct_fhir_vector_approach.py
- **FR-008**: System MUST support multi-modal search queries combining vector search, text search, and graph traversal
- **FR-009**: System MUST use Reciprocal Rank Fusion (RRF) to combine results from multiple search methods into unified ranking
- **FR-010**: System MUST support patient-specific filtering in queries using patient ID from FHIR Compartments field
- **FR-011**: System MUST use rag-templates GraphRAG pipeline from /Users/tdyar/ws/rag-templates for entity extraction and knowledge graph operations
- **FR-012**: System MUST connect to IRIS database at localhost:32782, namespace DEMO, using provided credentials
- **FR-013**: System MUST provide a YAML configuration file for BYOT mode that maps FHIR table columns to rag-templates expected schema
- **FR-014**: System MUST provide a FHIR document adapter that converts FHIR ResourceString JSON to rag-templates Document format
- **FR-015**: System MUST provide a setup script that initializes the GraphRAG pipeline and processes existing FHIR resources
- **FR-016**: System MUST provide a query interface that accepts natural language questions and returns multi-modal search results
- **FR-017**: System MUST handle errors gracefully when rag-templates library is unavailable or IRIS connection fails
- **FR-018**: System MUST make zero modifications to FHIR native table schema (HSFHIR_X0001_R.Rsrc)
- **FR-019**: System MUST use existing sentence-transformers embeddings (all-MiniLM-L6-v2, 384 dimensions) for consistency with current vector search
- **FR-020**: System MUST support both regex-based pattern matching and LLM-based entity extraction with configurable confidence thresholds

### Non-Functional Requirements

- **NFR-001**: Entity extraction MUST complete in under 2 seconds per document
- **NFR-002**: Knowledge graph build MUST complete in under 5 minutes for 51 DocumentReference resources
- **NFR-003**: Multi-modal queries MUST return results in under 1 second
- **NFR-004**: System MUST use connection pooling from rag-templates to manage database connections efficiently
- **NFR-005**: System MUST include error handling for database connection failures, malformed FHIR JSON, and missing rag-templates library
- **NFR-006**: System MUST include monitoring capabilities to track entity extraction metrics, query performance, and knowledge graph statistics
- **NFR-007**: System MUST maintain backward compatibility with existing direct_fhir_vector_approach.py implementation
- **NFR-008**: Configuration MUST be externalized in YAML files to support different environments without code changes

### Key Entities *(include if feature involves data)*

- **Medical Entity**: Represents a discrete medical concept extracted from clinical notes. Contains entity text, type classification (SYMPTOM, CONDITION, MEDICATION, PROCEDURE, BODY_PART, TEMPORAL), confidence score, and link to source FHIR resource. Entities have embeddings for vector search and participate in relationships.

- **Entity Relationship**: Represents a directed relationship between two medical entities. Contains source entity, target entity, relationship type (TREATS, CAUSES, LOCATED_IN, CO_OCCURS_WITH, PRECEDES), confidence score, and link to source FHIR resource where relationship was identified.

- **FHIR Document**: Represents a DocumentReference resource from FHIR native tables. Contains FHIR JSON with hex-encoded clinical notes, resource metadata (ResourceType, ResourceId, Compartments), and links to both vector embeddings and extracted entities.

- **Knowledge Graph**: The aggregate structure of all entities and relationships, forming a queryable medical knowledge network. Supports graph traversal queries to discover indirect relationships and related concepts.

- **Multi-Modal Search Result**: Represents the fusion of results from vector search, text search, and graph traversal. Contains ranked documents, contributing search methods, RRF scores, extracted entities, and discovered relationships.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Knowledge graph successfully extracts 100+ medical entities from 51 DocumentReference resources
- **SC-002**: Entity extraction accuracy achieves 80%+ precision on manual review of sample entities
- **SC-003**: Multi-modal search returns results combining at least two search methods (vector, text, or graph) for 90%+ of queries
- **SC-004**: Query response time improves by 20%+ in relevance compared to vector-only search (measured by user relevance ratings)
- **SC-005**: System processes all 51 existing DocumentReferences and builds complete knowledge graph in under 5 minutes
- **SC-006**: Zero modifications are made to FHIR native table schema, verified by schema comparison before and after implementation
- **SC-007**: Existing direct_fhir_vector_approach.py continues to function without modification after GraphRAG implementation
- **SC-008**: Entity extraction performance meets < 2 seconds per document for 95%+ of documents
- **SC-009**: Multi-modal queries return results in under 1 second for 95%+ of queries with knowledge graph size of 51 documents
- **SC-010**: System successfully identifies and stores at least 50 entity relationships (TREATS, CAUSES, etc.) from clinical notes

### Qualitative Outcomes

- Medical researchers can discover entity relationships not explicitly stated in individual clinical notes through graph traversal
- Clinicians receive more comprehensive search results that include related concepts discovered through knowledge graph
- System administrators can monitor knowledge graph statistics and query performance through built-in monitoring capabilities

## Assumptions

- The rag-templates library is available at /Users/tdyar/ws/rag-templates and supports BYOT (Bring Your Own Table) mode as documented
- IRIS database credentials (_SYSTEM/ISCDEMO) remain valid and have permissions to create new tables (RAG.Entities, RAG.EntityRelationships)
- The existing 51 DocumentReference resources contain sufficient medical content for meaningful entity extraction
- Clinical notes are in English and use standard medical terminology
- Entity extraction confidence threshold of 0.7 is acceptable for initial implementation
- RRF fusion with equal weights (vector_k=30, text_k=30, graph_k=10) provides balanced multi-modal results
- sentence-transformers library is already available in Python environment from existing implementation
- Ollama or similar LLM service is available for LLM-based entity extraction (fallback to regex patterns if unavailable)
- Performance targets (< 2 sec/doc, < 5 min total, < 1 sec query) are based on current dataset size of 51 documents
- No concurrent write conflicts during knowledge graph build as setup script runs single-threaded

## Dependencies

- **rag-templates library**: GraphRAG pipeline implementation at /Users/tdyar/ws/rag-templates
- **IRIS database**: Running instance at localhost:32782 with DEMO namespace
- **Python libraries**: iris-python-driver, sentence-transformers, PyYAML
- **Existing implementation**: direct_fhir_vector_approach.py and VectorSearch.FHIRResourceVectors table
- **FHIR data**: 51 DocumentReference resources in HSFHIR_X0001_R.Rsrc table
- **LLM service** (optional): Ollama or similar for enhanced entity extraction beyond regex patterns

## Out of Scope

- Migration of existing FHIR data to new schema or external systems
- Real-time entity extraction on FHIR resource creation (batch processing only in initial implementation)
- Integration with external medical ontologies (SNOMED CT, ICD-10) beyond basic entity type classification
- User interface for knowledge graph visualization or exploration
- Multi-language support for clinical notes (English only)
- FHIR resource types beyond DocumentReference
- Authentication and authorization for multi-user scenarios
- Deployment automation or containerization
- Performance optimization for datasets larger than 100 documents (optimization can be added later based on actual growth)
- Automated retraining or updating of entity extraction models
