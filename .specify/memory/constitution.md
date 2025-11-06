# FHIR AI Hackathon Kit Constitution

## Core Principles

### I. Data Integrity
- No modifications to source FHIR data (read-only overlay via BYOT)
- Existing FHIR native tables must remain untouched
- All integrations must preserve existing functionality

### II. Backward Compatibility
- Existing implementations must continue functioning after any changes
- direct_fhir_vector_approach.py must remain operational
- VectorSearch.FHIRResourceVectors table must be preserved

### III. InterSystems IRIS Vector Support
**CRITICAL KNOWLEDGE**:
- IRIS has **native VECTOR type support** - use `VECTOR(DOUBLE, 384)` in DDL
- IRIS client libraries (Python iris driver, JDBC, etc.) **do not recognize** the VECTOR type in their metadata
- When querying INFORMATION_SCHEMA.COLUMNS, vectors appear as `VARCHAR` - **this is a client limitation, NOT the actual storage type**
- **NEVER change VECTOR to VARCHAR based on INFORMATION_SCHEMA output**
- The database stores vectors natively and performs optimized vector operations
- Vector indexes use IRIS-specific syntax (to be determined from working examples)

### IV. Testability
- All entity extraction and query logic must be independently testable
- Unit tests for components, integration tests for end-to-end workflows
- Test fixtures must represent realistic FHIR data

### V. Performance
- Sub-second query response times required for acceptable user experience
- Entity extraction: < 2 seconds per document
- Knowledge graph build: < 5 minutes for 51 documents
- Multi-modal queries: < 1 second response time

## Technical Standards

### Database Schema
- Use IRIS native types: BIGINT, VARCHAR, FLOAT, TIMESTAMP, VECTOR
- AUTO_INCREMENT for primary keys
- Foreign key constraints with CASCADE for data integrity
- Indexes on frequently queried columns

### Configuration Management
- External YAML configuration for environment-specific settings
- Centralized config in `config/fhir_graphrag_config.yaml`
- No hardcoded credentials or paths in source code

### Error Handling
- Graceful degradation when optional services (LLM) unavailable
- Clear error messages with context for debugging
- Fail-fast for required dependencies

## Governance

Constitution supersedes implementation assumptions. When in doubt about IRIS capabilities, consult working examples or documentation rather than making assumptions based on client library behavior.

**Version**: 1.0.0 | **Ratified**: 2025-11-06 | **Last Amended**: 2025-11-06
