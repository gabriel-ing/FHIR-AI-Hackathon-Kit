# GraphRAG Implementation Plan for FHIR Native Tables

**Date**: 2025-11-05
**Objective**: Implement GraphRAG using rag-templates library with BYOT (Bring Your Own Table) overlay mode on FHIR native tables

---

## Executive Summary

This plan leverages the **rag-templates** GraphRAG framework to add knowledge graph capabilities to our existing direct FHIR integration (proven in `direct_fhir_vector_approach.py`). By using the BYOT/overlay mode, we can:

1. **Zero-copy integration** - No data migration from FHIR native tables
2. **Knowledge graph enrichment** - Extract medical entities and relationships
3. **Multi-modal search** - Combine vector, text, and graph traversal
4. **Production-ready** - Enterprise-grade RAG with proper connection pooling and error handling

---

## Architecture Overview

### Current State (from direct_fhir_vector_approach.py)
```
HSFHIR_X0001_R.Rsrc (FHIR native table)
  ├─ ResourceString (FHIR JSON with clinical notes)
  ├─ ResourceType, ResourceId, Compartments
  └─ Deleted flag

VectorSearch.FHIRResourceVectors (companion vector table)
  ├─ ResourceID → joins to Rsrc.ID
  ├─ Vector (384 dimensions)
  ├─ ResourceType, VectorModel
  └─ LastUpdated
```

### Target State (GraphRAG with BYOT)
```
HSFHIR_X0001_R.Rsrc (FHIR native - unchanged)
  │
  ├─→ VectorSearch.FHIRResourceVectors (vectors - existing)
  │
  └─→ RAG.Entities (medical entities - NEW)
      ├─ EntityID, EntityText, EntityType
      ├─ ResourceID → joins to Rsrc.ID
      └─ Confidence, EmbeddingVector

      └─→ RAG.EntityRelationships (relationships - NEW)
          ├─ SourceEntityID, TargetEntityID
          ├─ RelationshipType (TREATS, CAUSES, etc.)
          ├─ ResourceID → joins to Rsrc.ID
          └─ Confidence
```

---

## Implementation Strategy

### Phase 1: BYOT Configuration for FHIR Tables

**Goal**: Configure rag-templates to use FHIR native tables as source data

#### Step 1.1: Create Custom Configuration

Create `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/config/fhir_graphrag_config.yaml`:

```yaml
# FHIR GraphRAG Configuration
database:
  iris:
    host: "localhost"
    port: 32782  # FHIR server port
    namespace: "DEMO"
    username: "_SYSTEM"
    password: "ISCDEMO"

# BYOT Configuration - Map to FHIR native tables
storage:
  iris:
    table_name: "HSFHIR_X0001_R.Rsrc"  # BYOT: Use existing FHIR table
    column_mapping:
      id_column: "ID"                   # Primary key
      text_column: "ResourceString"     # FHIR JSON
      metadata_columns:
        - "ResourceType"
        - "ResourceId"
        - "Compartments"
        - "Deleted"
    zero_copy: true                     # No data migration
    preserve_schema: true               # Read-only overlay

# Vector storage - use our existing companion table
vector_storage:
  table_name: "VectorSearch.FHIRResourceVectors"
  reference_column: "ResourceID"        # Links to Rsrc.ID

# GraphRAG Configuration
pipelines:
  graphrag:
    entity_extraction_enabled: true
    default_top_k: 10
    max_depth: 2                        # Graph traversal depth
    max_entities: 50

    # Medical entity types to extract
    entity_types:
      - "SYMPTOM"          # "cough", "fever", "chest pain"
      - "CONDITION"        # "diabetes", "hypertension", "COPD"
      - "MEDICATION"       # "aspirin", "metformin", "lisinopril"
      - "PROCEDURE"        # "blood test", "x-ray", "surgery"
      - "BODY_PART"        # "chest", "lungs", "heart"
      - "TEMPORAL"         # "2023-01-15", "3 days ago"

    # Relationship types
    relationship_types:
      - "TREATS"           # medication TREATS condition
      - "CAUSES"           # condition CAUSES symptom
      - "LOCATED_IN"       # symptom LOCATED_IN body_part
      - "CO_OCCURS_WITH"   # symptom CO_OCCURS_WITH symptom
      - "PRECEDES"         # event PRECEDES event (temporal)

embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  dimension: 384
  batch_size: 32
```

#### Step 1.2: Create FHIR Document Adapter

Create `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/fhir_document_adapter.py`:

```python
"""
FHIR Document Adapter for rag-templates BYOT mode
Extracts clinical notes from FHIR JSON for GraphRAG processing
"""

import json
from typing import List, Dict, Any
from iris_rag.core.models import Document

class FHIRDocumentAdapter:
    """
    Adapter to convert FHIR ResourceString JSON to rag-templates Document format
    """

    @staticmethod
    def extract_clinical_note(resource_string: str) -> str:
        """
        Extract clinical note text from FHIR DocumentReference JSON

        Args:
            resource_string: FHIR JSON string

        Returns:
            Decoded clinical note text
        """
        try:
            data = json.loads(resource_string)

            # Extract hex-encoded clinical note
            if 'content' in data and data['content']:
                encoded_data = data['content'][0]['attachment']['data']
                return bytes.fromhex(encoded_data).decode('utf-8', errors='replace')

            return ""
        except Exception as e:
            print(f"Failed to extract clinical note: {e}")
            return ""

    @staticmethod
    def fhir_row_to_document(row: tuple, column_names: List[str]) -> Document:
        """
        Convert FHIR table row to rag-templates Document

        Args:
            row: Database row tuple
            column_names: Column names matching row positions

        Returns:
            Document object ready for GraphRAG processing
        """
        # Create column mapping
        row_dict = dict(zip(column_names, row))

        # Extract fields
        doc_id = row_dict['ID']
        resource_string = row_dict['ResourceString']
        resource_type = row_dict['ResourceType']
        resource_id = row_dict['ResourceId']
        compartments = row_dict.get('Compartments', '')

        # Extract clinical note text
        clinical_note = FHIRDocumentAdapter.extract_clinical_note(resource_string)

        # Extract patient ID from compartments
        patient_id = None
        if compartments and 'Patient/' in compartments:
            import re
            match = re.search(r'Patient/(\d+)', compartments)
            if match:
                patient_id = match.group(1)

        # Create Document
        return Document(
            id=str(doc_id),
            page_content=clinical_note,
            metadata={
                'resource_type': resource_type,
                'resource_id': resource_id,
                'patient_id': patient_id,
                'compartments': compartments,
                'source': 'FHIR_DocumentReference',
                'fhir_native_id': doc_id
            }
        )

    @staticmethod
    def load_fhir_documents(cursor, patient_id: str = None) -> List[Document]:
        """
        Load FHIR DocumentReference resources as Documents

        Args:
            cursor: Database cursor
            patient_id: Optional patient filter

        Returns:
            List of Document objects
        """
        sql = """
        SELECT ID, ResourceString, ResourceType, ResourceId, Compartments
        FROM HSFHIR_X0001_R.Rsrc
        WHERE ResourceType = 'DocumentReference'
          AND Deleted = 0
        """

        if patient_id:
            sql += f" AND Compartments LIKE '%Patient/{patient_id}%'"

        cursor.execute(sql)
        rows = cursor.fetchall()
        column_names = ['ID', 'ResourceString', 'ResourceType', 'ResourceId', 'Compartments']

        return [
            FHIRDocumentAdapter.fhir_row_to_document(row, column_names)
            for row in rows
        ]
```

---

### Phase 2: GraphRAG Pipeline Integration

**Goal**: Set up GraphRAG pipeline with medical entity extraction

#### Step 2.1: Create GraphRAG Initialization Script

Create `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/fhir_graphrag_setup.py`:

```python
#!/usr/bin/env python3
"""
FHIR GraphRAG Setup
Initialize GraphRAG pipeline with FHIR native table overlay
"""

import sys
import os

# Add rag-templates to path
sys.path.insert(0, '/Users/tdyar/ws/rag-templates')
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit')

import iris
from iris_rag import create_pipeline
from iris_rag.config.manager import ConfigurationManager
from iris_rag.core.connection import ConnectionManager
from fhir_document_adapter import FHIRDocumentAdapter

def setup_graphrag_pipeline():
    """
    Initialize GraphRAG pipeline with FHIR native tables
    """

    print("=" * 80)
    print("FHIR GraphRAG Setup - BYOT Mode")
    print("=" * 80)

    # Step 1: Load custom configuration
    print("\n[Step 1] Loading FHIR GraphRAG configuration...")
    config_path = '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/config/fhir_graphrag_config.yaml'

    # Initialize with custom config
    os.environ['RAG_CONFIG_PATH'] = config_path

    # Step 2: Create GraphRAG pipeline
    print("\n[Step 2] Creating GraphRAG pipeline...")
    pipeline = create_pipeline(
        'graphrag',
        validate_requirements=True
    )

    print(f"✅ GraphRAG pipeline initialized")
    print(f"   - Entity extraction: {pipeline.entity_extraction_enabled}")
    print(f"   - Max graph depth: {pipeline.max_depth}")
    print(f"   - Max entities: {pipeline.max_entities}")

    # Step 3: Load FHIR documents using BYOT adapter
    print("\n[Step 3] Loading FHIR documents from native tables...")

    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    # Load all DocumentReference resources
    documents = FHIRDocumentAdapter.load_fhir_documents(cursor)
    print(f"✅ Loaded {len(documents)} FHIR DocumentReference resources")

    # Step 4: Process documents with GraphRAG
    print("\n[Step 4] Processing documents with entity extraction...")
    print("   This will extract medical entities and relationships...")

    pipeline.load_documents(
        documents_path="",  # Not used with BYOT
        documents=documents,
        generate_embeddings=False  # We already have vectors
    )

    print(f"✅ GraphRAG processing complete!")

    # Step 5: Verify knowledge graph
    print("\n[Step 5] Verifying knowledge graph...")

    cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
    entity_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM RAG.EntityRelationships")
    relationship_count = cursor.fetchone()[0]

    print(f"✅ Knowledge graph populated:")
    print(f"   - Entities: {entity_count}")
    print(f"   - Relationships: {relationship_count}")

    # Show sample entities
    cursor.execute("""
        SELECT EntityText, EntityType, Confidence
        FROM RAG.Entities
        ORDER BY Confidence DESC
        LIMIT 10
    """)

    print("\n   Sample extracted entities:")
    for entity_text, entity_type, confidence in cursor.fetchall():
        print(f"   - {entity_text} ({entity_type}): {confidence:.2f}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ FHIR GraphRAG Setup Complete!")
    print("=" * 80)

    return pipeline

if __name__ == "__main__":
    pipeline = setup_graphrag_pipeline()
```

---

### Phase 3: GraphRAG Query Interface

**Goal**: Implement multi-modal search (vector + text + graph)

#### Step 3.1: Create GraphRAG Query Script

Create `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/fhir_graphrag_query.py`:

```python
#!/usr/bin/env python3
"""
FHIR GraphRAG Query Interface
Multi-modal search combining vector, text, and knowledge graph
"""

import sys
sys.path.insert(0, '/Users/tdyar/ws/rag-templates')
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit')

from iris_rag import create_pipeline
import json

def graphrag_query(query: str, patient_id: str = None, top_k: int = 5):
    """
    Query FHIR data using GraphRAG multi-modal search

    Args:
        query: Natural language question
        patient_id: Optional patient filter
        top_k: Number of results to return

    Returns:
        Results with answer, contexts, and entities
    """

    print("=" * 80)
    print(f"GraphRAG Query: {query}")
    if patient_id:
        print(f"Patient: {patient_id}")
    print("=" * 80)

    # Initialize pipeline
    pipeline = create_pipeline('graphrag')

    # Build metadata filter for patient
    metadata_filter = {}
    if patient_id:
        metadata_filter['patient_id'] = patient_id

    # Execute GraphRAG query (uses RRF fusion of vector + text + graph)
    result = pipeline.query(
        query=query,
        top_k=top_k,
        method='rrf',              # Reciprocal Rank Fusion
        vector_k=30,               # Top 30 from vector search
        text_k=30,                 # Top 30 from text search
        graph_k=10,                # Top 10 from graph traversal
        generate_answer=True,      # LLM-generated answer
        metadata_filter=metadata_filter
    )

    # Display results
    print(f"\n📊 Search Results:")
    print(f"   - Retrieved: {len(result['retrieved_documents'])} documents")
    print(f"   - Execution time: {result['execution_time']:.3f}s")
    print(f"   - Retrieval method: {result['metadata']['retrieval_method']}")

    if 'entities' in result['metadata']:
        print(f"\n🔬 Extracted Entities:")
        for entity in result['metadata']['entities'][:10]:
            print(f"   - {entity['text']} ({entity['type']})")

    if 'relationships' in result['metadata']:
        print(f"\n🔗 Relationships:")
        for rel in result['metadata']['relationships'][:5]:
            print(f"   - {rel['source']} → {rel['type']} → {rel['target']}")

    print(f"\n💡 Answer:")
    print(f"   {result['answer']}")

    print(f"\n📝 Sources:")
    for i, source in enumerate(result['sources'][:3], 1):
        print(f"   {i}. {source}")

    print("\n" + "=" * 80)

    return result

def demo_queries():
    """
    Run demonstration queries
    """

    queries = [
        {
            'query': "Has the patient reported any respiratory symptoms?",
            'patient_id': '3',
            'description': "Medical symptom search with entity extraction"
        },
        {
            'query': "What medications has the patient been prescribed?",
            'patient_id': '3',
            'description': "Medication extraction and relationship mapping"
        },
        {
            'query': "Timeline of patient's medical events",
            'patient_id': '3',
            'description': "Temporal relationship extraction"
        },
        {
            'query': "What conditions are associated with chest pain?",
            'patient_id': None,
            'description': "Knowledge graph traversal across all patients"
        }
    ]

    for i, q in enumerate(queries, 1):
        print(f"\n\n{'#' * 80}")
        print(f"Demo Query {i}: {q['description']}")
        print(f"{'#' * 80}\n")

        result = graphrag_query(
            query=q['query'],
            patient_id=q['patient_id'],
            top_k=5
        )

        input("\nPress Enter to continue to next query...")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Single query mode
        query = sys.argv[1]
        patient_id = sys.argv[2] if len(sys.argv) > 2 else None
        graphrag_query(query, patient_id)
    else:
        # Demo mode
        demo_queries()
```

---

### Phase 4: Enhanced Entity Extraction

**Goal**: Configure medical-specific entity extraction

#### Step 4.1: Create Medical Entity Extractor

Create `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/medical_entity_extractor.py`:

```python
"""
Medical Entity Extractor
Customized entity extraction for FHIR clinical notes
"""

from typing import List, Dict, Any
import re

class MedicalEntityExtractor:
    """
    Extract medical entities from clinical notes using:
    1. Pattern matching for common medical terms
    2. LLM-based extraction (via rag-templates EntityExtractionService)
    3. Medical ontology mapping (optional: SNOMED CT, ICD-10)
    """

    # Common medical patterns
    SYMPTOM_PATTERNS = [
        r'\b(pain|ache|fever|cough|nausea|vomiting|dizziness|fatigue|weakness)\b',
        r'\b(headache|chest pain|shortness of breath|difficulty breathing)\b',
        r'\b(swelling|rash|bleeding|discharge|numbness|tingling)\b'
    ]

    MEDICATION_PATTERNS = [
        r'\b([A-Z][a-z]+(?:pril|olol|statin|mycin|cillin))\b',  # Drug name patterns
        r'\b(aspirin|ibuprofen|acetaminophen|metformin|insulin)\b'
    ]

    TEMPORAL_PATTERNS = [
        r'\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\b',  # Dates
        r'\b(\d+\s+(?:days?|weeks?|months?|years?)\s+ago)\b',  # Relative time
        r'\b(yesterday|today|last\s+(?:week|month|year))\b'
    ]

    @staticmethod
    def extract_entities_regex(text: str) -> List[Dict[str, Any]]:
        """
        Quick regex-based entity extraction (fallback/supplement to LLM)
        """
        entities = []

        # Extract symptoms
        for pattern in MedicalEntityExtractor.SYMPTOM_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    'text': match.group(0),
                    'type': 'SYMPTOM',
                    'confidence': 0.7,  # Pattern-based confidence
                    'start': match.start(),
                    'end': match.end()
                })

        # Extract medications
        for pattern in MedicalEntityExtractor.MEDICATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    'text': match.group(0),
                    'type': 'MEDICATION',
                    'confidence': 0.7,
                    'start': match.start(),
                    'end': match.end()
                })

        # Extract temporal references
        for pattern in MedicalEntityExtractor.TEMPORAL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append({
                    'text': match.group(0),
                    'type': 'TEMPORAL',
                    'confidence': 0.8,  # High confidence for date patterns
                    'start': match.start(),
                    'end': match.end()
                })

        # Deduplicate overlapping entities
        entities = MedicalEntityExtractor._deduplicate_entities(entities)

        return entities

    @staticmethod
    def _deduplicate_entities(entities: List[Dict]) -> List[Dict]:
        """Remove overlapping entities, keeping highest confidence"""
        if not entities:
            return []

        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: e['start'])

        deduplicated = [sorted_entities[0]]
        for entity in sorted_entities[1:]:
            # Check for overlap with last added entity
            last = deduplicated[-1]
            if entity['start'] >= last['end']:
                # No overlap, add it
                deduplicated.append(entity)
            elif entity['confidence'] > last['confidence']:
                # Overlap but higher confidence, replace
                deduplicated[-1] = entity

        return deduplicated
```

---

## Testing Strategy

### Test 1: Entity Extraction Verification

```python
# Test entity extraction on sample clinical note
from medical_entity_extractor import MedicalEntityExtractor

sample_note = """
Patient reports persistent cough and chest pain for 3 days.
Prescribed lisinopril 10mg daily for hypertension.
Follow-up scheduled for 2023-05-15.
"""

entities = MedicalEntityExtractor.extract_entities_regex(sample_note)
print(f"Extracted {len(entities)} entities:")
for entity in entities:
    print(f"  - {entity['text']} ({entity['type']}): {entity['confidence']}")

# Expected output:
# - cough (SYMPTOM): 0.7
# - chest pain (SYMPTOM): 0.7
# - lisinopril (MEDICATION): 0.7
# - 2023-05-15 (TEMPORAL): 0.8
```

### Test 2: GraphRAG Query Validation

```bash
# Run setup
python3 fhir_graphrag_setup.py

# Run test queries
python3 fhir_graphrag_query.py "Has the patient had any respiratory issues?" 3

# Expected: Returns DocumentReferences with respiratory symptoms,
#           extracts symptom entities, shows relationships
```

### Test 3: Performance Benchmarks

- **Entity extraction**: < 2 seconds per document
- **Knowledge graph build**: < 5 minutes for 51 documents
- **GraphRAG query**: < 1 second (vector + graph fusion)

---

## Success Criteria

✅ **Phase 1 Complete**: BYOT configuration loads FHIR native tables
✅ **Phase 2 Complete**: GraphRAG extracts 100+ medical entities
✅ **Phase 3 Complete**: Multi-modal queries return accurate results
✅ **Phase 4 Complete**: Medical entity types correctly identified

---

## Advantages Over Current Approach

| Feature | Current (direct_fhir_vector_approach.py) | GraphRAG with rag-templates |
|---------|----------------------------------------|----------------------------|
| Data source | Direct SQL on FHIR tables | ✅ Same (BYOT overlay) |
| Vector search | Manual VECTOR_COSINE query | ✅ Automated with connection pooling |
| Entity extraction | None | ✅ **Medical entities (symptoms, meds, conditions)** |
| Relationship mapping | None | ✅ **Entity relationships (TREATS, CAUSES)** |
| Knowledge graph | None | ✅ **Graph traversal for related entities** |
| Multi-modal search | Vector only | ✅ **Vector + Text + Graph (RRF fusion)** |
| LLM integration | Manual Ollama calls | ✅ Built-in with context management |
| Production features | Manual connection handling | ✅ Connection pooling, error handling, monitoring |

---

## Next Steps

1. **Create directory structure**:
   ```bash
   mkdir -p /Users/tdyar/ws/FHIR-AI-Hackathon-Kit/config
   ```

2. **Implement Phase 1**: BYOT configuration and adapter

3. **Test on existing data**: 51 DocumentReference resources from Patient 3

4. **Validate entity extraction**: Verify medical entities are correctly identified

5. **Benchmark performance**: Compare GraphRAG vs. current vector-only approach

6. **Document results**: Update DIRECT_FHIR_VECTOR_SUCCESS.md with GraphRAG findings

---

## Files to Create

1. `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/config/fhir_graphrag_config.yaml`
2. `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/fhir_document_adapter.py`
3. `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/fhir_graphrag_setup.py`
4. `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/fhir_graphrag_query.py`
5. `/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/medical_entity_extractor.py`

---

**Status**: Ready for implementation
**Estimated time**: 2-3 hours for complete setup and testing
**Risk level**: Low (uses proven BYOT approach from rag-templates)
