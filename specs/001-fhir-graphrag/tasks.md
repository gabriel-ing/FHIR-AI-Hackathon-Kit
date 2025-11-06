# Tasks: FHIR GraphRAG Knowledge Graph

**Input**: Design documents from `/specs/001-fhir-graphrag/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single Python project**: `src/`, `tests/`, `config/` at repository root
- Paths assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure (src/adapters/, src/extractors/, src/setup/, src/query/, tests/integration/, tests/unit/, tests/fixtures/, config/)
- [X] T002 [P] Create Python .gitignore with venv/, __pycache__/, *.pyc, .env*, dist/, *.egg-info/, logs/
- [X] T003 [P] Create config/fhir_graphrag_config.yaml from contracts/byot-config-schema.yaml template
- [X] T004 [P] Verify rag-templates library accessibility at /Users/tdyar/ws/rag-templates
- [X] T005 [P] Create tests/fixtures/sample_fhir_resources.json with sample DocumentReference FHIR JSON
- [X] T006 [P] Create tests/fixtures/expected_entities.json with expected entity extraction results

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create RAG.Entities table DDL from contracts/entity-schema.json (EntityID, EntityText, EntityType, ResourceID, Confidence, EmbeddingVector, ExtractedAt, ExtractedBy)
- [X] T008 Create RAG.EntityRelationships table DDL from contracts/relationship-schema.json (RelationshipID, SourceEntityID, TargetEntityID, RelationshipType, ResourceID, Confidence, ExtractedAt, Context)
- [X] T009 Create database table creation script in src/setup/create_knowledge_graph_tables.py
- [X] T010 Verify FHIR native table accessibility (HSFHIR_X0001_R.Rsrc with 51 DocumentReference resources)
- [X] T011 Verify existing vector table (VectorSearch.FHIRResourceVectors) is preserved and functional

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Extract Medical Knowledge Graph (Priority: P1) 🎯 MVP

**Goal**: Extract structured medical knowledge (symptoms, conditions, medications, procedures) from unstructured clinical notes and store in knowledge graph tables

**Independent Test**: Run setup script on 51 DocumentReference resources and verify 100+ entities extracted in RAG.Entities and 50+ relationships in RAG.EntityRelationships with correct types and confidence scores

### Implementation for User Story 1

- [X] T012 [P] [US1] Create FHIR document adapter class in src/adapters/fhir_document_adapter.py with extract_clinical_note() method (decode hex from FHIR JSON)
- [X] T013 [P] [US1] Add fhir_row_to_document() method in src/adapters/fhir_document_adapter.py (convert FHIR table row to rag-templates Document format)
- [X] T014 [P] [US1] Add load_fhir_documents() method in src/adapters/fhir_document_adapter.py (query FHIR native tables and convert to Documents)
- [X] T015 [P] [US1] Create medical entity extractor in src/extractors/medical_entity_extractor.py with regex patterns for SYMPTOM, CONDITION, MEDICATION entity types
- [X] T016 [P] [US1] Add regex patterns for PROCEDURE, BODY_PART, TEMPORAL entity types in src/extractors/medical_entity_extractor.py
- [X] T017 [P] [US1] Implement extract_entities_regex() method in src/extractors/medical_entity_extractor.py with confidence scoring
- [X] T018 [US1] Add entity deduplication logic in src/extractors/medical_entity_extractor.py (_deduplicate_entities method)
- [X] T019 [US1] Create GraphRAG setup script in src/setup/fhir_graphrag_setup.py with --mode=init for table creation
- [X] T020 [US1] Add --mode=build in src/setup/fhir_graphrag_setup.py to load BYOT config and initialize rag-templates GraphRAG pipeline
- [X] T021 [US1] Implement document loading in src/setup/fhir_graphrag_setup.py using FHIRDocumentAdapter
- [X] T022 [US1] Add entity extraction integration in src/setup/fhir_graphrag_setup.py (call pipeline.load_documents with entity_extraction_enabled=true)
- [X] T023 [US1] Add relationship extraction integration in src/setup/fhir_graphrag_setup.py (extract TREATS, CAUSES, LOCATED_IN, CO_OCCURS_WITH, PRECEDES relationships)
- [X] T024 [US1] Implement knowledge graph statistics reporting in src/setup/fhir_graphrag_setup.py (entity count, relationship count, processing time)
- [X] T025 [US1] Add --mode=stats in src/setup/fhir_graphrag_setup.py to query and display knowledge graph statistics
- [X] T026 [US1] Add error handling for missing rag-templates library in src/setup/fhir_graphrag_setup.py
- [X] T027 [US1] Add error handling for IRIS connection failures in src/setup/fhir_graphrag_setup.py
- [X] T028 [US1] Add error handling for malformed FHIR JSON in src/adapters/fhir_document_adapter.py
- [X] T029 [US1] Add logging for entity extraction progress (document X/N, entities extracted, time per document) in src/setup/fhir_graphrag_setup.py
- [X] T030 [US1] Add validation for BYOT configuration (required fields, table name validation) in src/setup/fhir_graphrag_setup.py

**Checkpoint**: At this point, User Story 1 should be fully functional - running fhir_graphrag_setup.py should extract 100+ entities and 50+ relationships from 51 DocumentReferences

---

## Phase 4: User Story 2 - Multi-Modal Medical Search (Priority: P2)

**Goal**: Query patient medical history using natural language with results combining vector similarity, text matching, and graph traversal using RRF fusion

**Independent Test**: Run queries like "respiratory symptoms" or "medications for hypertension" and verify results include vector-matched documents, text-matched keywords, and graph-traversed related entities with RRF scores

### Implementation for User Story 2

- [ ] T031 [US2] Create query interface script in src/query/fhir_graphrag_query.py with graphrag_query() function accepting query string and optional patient_id
- [ ] T032 [US2] Initialize rag-templates GraphRAG pipeline in src/query/fhir_graphrag_query.py (create_pipeline('graphrag') with BYOT config)
- [ ] T033 [US2] Implement multi-modal search execution in src/query/fhir_graphrag_query.py (pipeline.query with method='rrf', vector_k=30, text_k=30, graph_k=10)
- [ ] T034 [US2] Add patient-specific filtering in src/query/fhir_graphrag_query.py (metadata_filter with patient_id from Compartments field)
- [ ] T035 [US2] Implement result display in src/query/fhir_graphrag_query.py (show retrieved documents, execution time, retrieval method, extracted entities, relationships, LLM answer)
- [ ] T036 [US2] Add command-line argument parsing in src/query/fhir_graphrag_query.py (query, --patient, --top-k, --vector-k, --text-k, --graph-k)
- [ ] T037 [US2] Create demo_queries() function in src/query/fhir_graphrag_query.py with 4 predefined queries (respiratory symptoms, medications, timeline, condition-symptom relationships)
- [ ] T038 [US2] Add RRF score display in src/query/fhir_graphrag_query.py results (show contribution from vector, text, graph sources)
- [ ] T039 [US2] Implement entity relationship traversal display in src/query/fhir_graphrag_query.py (show discovered relationships from graph traversal)
- [ ] T040 [US2] Add error handling for empty knowledge graph in src/query/fhir_graphrag_query.py
- [ ] T041 [US2] Add error handling for no results found in src/query/fhir_graphrag_query.py
- [ ] T042 [US2] Add logging for query performance metrics in src/query/fhir_graphrag_query.py (query latency, number of results, search methods used)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - queries return multi-modal results with RRF fusion

---

## Phase 5: User Story 3 - Performance-Optimized Knowledge Graph Queries (Priority: P3)

**Goal**: Ensure knowledge graph queries complete within performance targets (< 2 sec/doc extraction, < 5 min total build, < 1 sec query)

**Independent Test**: Run performance benchmarks and verify entity extraction < 2 sec/doc, knowledge graph build < 5 min for 51 docs, queries < 1 sec response time

### Implementation for User Story 3

- [ ] T043 [P] [US3] Add batch processing for entity extraction in src/setup/fhir_graphrag_setup.py (batch_size=10 from config)
- [ ] T044 [P] [US3] Add parallel extraction support in src/setup/fhir_graphrag_setup.py (parallel_extraction=true, max_workers=4 from config)
- [ ] T045 [US3] Implement incremental processing in src/setup/fhir_graphrag_setup.py (skip already-processed ResourceIDs by checking RAG.Entities)
- [ ] T046 [US3] Add checkpoint/resume capability in src/setup/fhir_graphrag_setup.py (save progress, resume from last processed document)
- [ ] T047 [US3] Optimize database queries in src/adapters/fhir_document_adapter.py (use prepared statements, batch inserts)
- [ ] T048 [US3] Add connection pooling validation in src/setup/fhir_graphrag_setup.py (verify rag-templates connection pool configuration)
- [ ] T049 [US3] Implement performance metrics collection in src/setup/fhir_graphrag_setup.py (entity_extraction_time, entity_extraction_count, relationship_extraction_count)
- [ ] T050 [US3] Add performance metrics display in src/setup/fhir_graphrag_setup.py --mode=stats (avg time per document, p50/p95/p99 latencies)
- [ ] T051 [US3] Create performance benchmark script in tests/integration/test_performance_benchmarks.py (test entity extraction speed, knowledge graph build time, query latency)
- [ ] T052 [US3] Add query performance logging in src/query/fhir_graphrag_query.py (log query latency with p50/p95/p99 tracking)
- [ ] T053 [US3] Optimize vector search queries in src/query/fhir_graphrag_query.py (use vector index hints for IRIS)
- [ ] T054 [US3] Add result pagination in src/query/fhir_graphrag_query.py (limit initial results, support offset for large result sets)

**Checkpoint**: All user stories should now be independently functional with performance targets met

---

## Phase 6: Integration Testing

**Purpose**: Validate end-to-end workflows and edge cases

- [ ] T055 [P] Create integration test for BYOT overlay in tests/integration/test_byot_overlay.py (verify FHIR table access without schema modification)
- [ ] T056 [P] Create integration test for entity extraction in tests/integration/test_entity_extraction.py (verify 100+ entities extracted with correct types and confidence scores)
- [ ] T057 [P] Create integration test for multi-modal search in tests/integration/test_multimodal_search.py (verify RRF fusion combines vector, text, graph results)
- [ ] T058 [P] Create unit test for FHIR adapter in tests/unit/test_fhir_adapter.py (test hex decoding, Document conversion, patient ID extraction)
- [ ] T059 [P] Create unit test for entity extractor in tests/unit/test_entity_extractor.py (test regex patterns, confidence scoring, deduplication)
- [ ] T060 Test edge case: empty clinical notes in tests/integration/test_edge_cases.py (verify graceful handling with no entities extracted)
- [ ] T061 Test edge case: malformed FHIR JSON in tests/integration/test_edge_cases.py (verify error handling with clear error messages)
- [ ] T062 Test edge case: low confidence entities in tests/integration/test_edge_cases.py (verify entities below threshold are filtered out)
- [ ] T063 Test edge case: duplicate entities in tests/integration/test_edge_cases.py (verify deduplication logic prevents duplicates)
- [ ] T064 Test backward compatibility in tests/integration/test_backward_compatibility.py (verify direct_fhir_vector_approach.py still works after GraphRAG implementation)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T065 [P] Add comprehensive docstrings to all modules (src/adapters/fhir_document_adapter.py, src/extractors/medical_entity_extractor.py, src/setup/fhir_graphrag_setup.py, src/query/fhir_graphrag_query.py)
- [ ] T066 [P] Create README.md in project root with setup instructions (refer to quickstart.md)
- [ ] T067 [P] Add type hints to all Python functions (use typing module for better IDE support)
- [ ] T068 Code cleanup and refactoring (remove debug prints, standardize error messages, consistent naming)
- [ ] T069 Add security validation for BYOT table names in src/setup/fhir_graphrag_setup.py (SQL injection prevention per BYOT spec)
- [ ] T070 Add monitoring metrics output in src/setup/fhir_graphrag_setup.py (JSON format for Prometheus/Grafana integration)
- [ ] T071 Validate quickstart.md instructions (run through setup steps and verify all commands work)
- [ ] T072 [P] Create example queries documentation in examples/sample_queries.md
- [ ] T073 [P] Add troubleshooting guide in docs/troubleshooting.md (common errors and solutions from quickstart.md)
- [ ] T074 Final validation: Run full end-to-end workflow (setup tables → build knowledge graph → run queries → verify results match success criteria SC-001 through SC-010)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T006) - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion (T007-T011)
  - User Story 1 (P1): Can start after Foundational
  - User Story 2 (P2): Depends on User Story 1 completion (needs knowledge graph populated)
  - User Story 3 (P3): Can enhance User Stories 1 and 2 in parallel (performance optimizations)
- **Integration Testing (Phase 6)**: Depends on User Story implementations
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Foundation for all other stories
- **User Story 2 (P2)**: Depends on User Story 1 (needs entities and relationships extracted) - Can test independently once US1 complete
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Optimizes US1 and US2, independently testable via benchmarks

### Within Each User Story

**User Story 1 (Entity Extraction)**:
- T012-T014 (FHIR adapter methods) can run in parallel [P]
- T015-T017 (entity extractor patterns and methods) can run in parallel [P]
- T018 (deduplication) depends on T017
- T019 (setup script init mode) can run in parallel with T012-T018 [P]
- T020-T024 (setup script build mode) run sequentially after T012-T018 complete
- T025-T030 (stats, error handling, logging) can run in parallel after T020-T024 [P]

**User Story 2 (Multi-Modal Search)**:
- All T031-T042 tasks modify src/query/fhir_graphrag_query.py so must run sequentially
- However, T031-T036 (core query logic) can be implemented first
- T037-T042 (demo queries, display, error handling) can follow

**User Story 3 (Performance)**:
- T043-T044 (batch/parallel processing) can run in parallel [P]
- T045-T046 (incremental/resume) can run in parallel [P] with T043-T044
- T047-T048 (DB optimization, pooling) can run in parallel [P]
- T049-T052 (metrics collection/display) can run in parallel [P]
- T053-T054 (query optimizations) can run in parallel [P] with T049-T052

### Parallel Opportunities

- **Phase 1 Setup**: T002, T003, T004, T005, T006 all [P]
- **Phase 3 US1**: T012-T017, T019 all [P] initially, then T025-T030 all [P] after core complete
- **Phase 5 US3**: Most tasks [P] as they optimize different components
- **Phase 6 Integration**: T055-T059 all [P] (different test files)
- **Phase 7 Polish**: T065, T066, T067, T072, T073 all [P]

---

## Parallel Example: User Story 1 (Entity Extraction)

```bash
# Launch all FHIR adapter methods together:
Task T012: "Create FHIR document adapter class in src/adapters/fhir_document_adapter.py with extract_clinical_note()"
Task T013: "Add fhir_row_to_document() method in src/adapters/fhir_document_adapter.py"
Task T014: "Add load_fhir_documents() method in src/adapters/fhir_document_adapter.py"

# Launch all entity extractor patterns together:
Task T015: "Create medical entity extractor in src/extractors/medical_entity_extractor.py with regex patterns for SYMPTOM, CONDITION, MEDICATION"
Task T016: "Add regex patterns for PROCEDURE, BODY_PART, TEMPORAL in src/extractors/medical_entity_extractor.py"
Task T017: "Implement extract_entities_regex() method in src/extractors/medical_entity_extractor.py"

# Launch error handling and logging together (after core is complete):
Task T025: "Add --mode=stats in src/setup/fhir_graphrag_setup.py"
Task T026: "Add error handling for missing rag-templates library in src/setup/fhir_graphrag_setup.py"
Task T027: "Add error handling for IRIS connection failures in src/setup/fhir_graphrag_setup.py"
Task T028: "Add error handling for malformed FHIR JSON in src/adapters/fhir_document_adapter.py"
Task T029: "Add logging for entity extraction progress in src/setup/fhir_graphrag_setup.py"
Task T030: "Add validation for BYOT configuration in src/setup/fhir_graphrag_setup.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T011) - CRITICAL blocks all stories
3. Complete Phase 3: User Story 1 (T012-T030)
4. **STOP and VALIDATE**: Run `python3 src/setup/fhir_graphrag_setup.py --mode=build` and verify:
   - 100+ entities extracted in RAG.Entities
   - 50+ relationships in RAG.EntityRelationships
   - Processing completes in < 5 minutes
   - Success Criteria SC-001, SC-005, SC-006, SC-008 met
5. Deploy/demo knowledge graph extraction capability

### Incremental Delivery

1. **Foundation** (T001-T011) → Foundation ready
2. **MVP: User Story 1** (T012-T030) → Test independently → **Deploy/Demo** (Knowledge graph extraction working!)
3. **User Story 2** (T031-T042) → Test independently → **Deploy/Demo** (Multi-modal search working!)
4. **User Story 3** (T043-T054) → Test independently → **Deploy/Demo** (Performance optimized!)
5. **Integration Tests** (T055-T064) → Validate edge cases and backward compatibility
6. **Polish** (T065-T074) → Production ready
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup (T001-T006) and Foundational (T007-T011) together
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T012-T030) - Entity extraction foundation
3. After User Story 1 complete:
   - **Developer B**: User Story 2 (T031-T042) - Multi-modal search
   - **Developer C**: User Story 3 (T043-T054) - Performance optimization (can start in parallel with US2)
4. Stories complete and integrate independently

---

## Success Criteria Mapping

| Success Criterion | Validated By Tasks | Target |
|-------------------|-------------------|--------|
| **SC-001**: Extract 100+ entities | T012-T024, T056 | 100+ medical entities from 51 docs |
| **SC-002**: 80%+ accuracy | T015-T017, T059 | Manual review sample entities |
| **SC-003**: Multi-modal 90%+ | T031-T042, T057 | RRF combines 2+ methods |
| **SC-005**: < 5 min build time | T019-T024, T049-T050, T051 | 3-4 min expected |
| **SC-006**: Zero FHIR modifications | T007-T011, T055, T064 | Schema comparison |
| **SC-007**: Backward compatibility | T064 | direct_fhir_vector_approach.py works |
| **SC-008**: < 2 sec/doc extraction | T049-T051 | 95%+ docs under threshold |
| **SC-009**: < 1 sec query time | T031-T042, T051-T052 | 95%+ queries under threshold |
| **SC-010**: 50+ relationships | T023, T056 | TREATS, CAUSES, etc. identified |

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [US1/US2/US3] labels map tasks to specific user stories for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Configuration from config/fhir_graphrag_config.yaml drives behavior (entity types, thresholds, performance settings)

---

## Task Summary

**Total Tasks**: 74
**Setup**: 6 tasks
**Foundational**: 5 tasks (BLOCKS user stories)
**User Story 1 (P1)**: 19 tasks (T012-T030) - MVP foundation
**User Story 2 (P2)**: 12 tasks (T031-T042) - Core value delivery
**User Story 3 (P3)**: 12 tasks (T043-T054) - Performance optimization
**Integration Testing**: 10 tasks (T055-T064) - Quality assurance
**Polish**: 10 tasks (T065-T074) - Production readiness

**Parallel Opportunities**: 25+ tasks marked [P]
**MVP Scope**: Phases 1-3 (T001-T030) = 30 tasks
**Full Feature**: All 74 tasks

**Estimated Implementation Time**:
- MVP (US1 only): 15-20 hours
- With US2: 25-30 hours
- With US3: 35-40 hours
- Full feature with tests and polish: 45-50 hours
