"""
FHIR Knowledge Graph Trigger Helper

This module is called by IRIS triggers via Embedded Python to extract
entities and relationships from FHIR resources.
"""

import json
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.extractors.medical_entity_extractor import MedicalEntityExtractor
import iris


def extract_and_store_entities(resource_id: int, resource_string: str):
    """
    Extract entities from FHIR resource and store in knowledge graph.

    Called by IRIS trigger via Embedded Python.

    Args:
        resource_id: FHIR resource ID
        resource_string: FHIR JSON as string
    """
    try:
        # Parse FHIR JSON
        fhir_json = json.loads(resource_string)

        # Extract clinical note (hex-decode)
        if "content" not in fhir_json or not fhir_json["content"]:
            return

        attachment = fhir_json["content"][0].get("attachment", {})
        hex_data = attachment.get("data")

        if not hex_data:
            return

        # Decode clinical note
        clinical_note = bytes.fromhex(hex_data).decode('utf-8', errors='replace')

        # Extract entities
        extractor = MedicalEntityExtractor(min_confidence=0.7)
        entities = extractor.extract_entities(clinical_note)

        # Get current IRIS connection from embedded context
        conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
        cursor = conn.cursor()

        # First, delete existing entities for this resource (update scenario)
        cursor.execute("DELETE FROM RAG.EntityRelationships WHERE ResourceID = ?", [resource_id])
        cursor.execute("DELETE FROM RAG.Entities WHERE ResourceID = ?", [resource_id])

        # Store entities
        entity_ids = {}
        for entity in entities:
            cursor.execute("""
                INSERT INTO RAG.Entities
                (EntityText, EntityType, ResourceID, Confidence, ExtractedBy, ExtractedAt)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                entity['text'],
                entity['type'],
                resource_id,
                entity['confidence'],
                entity.get('method', 'hybrid')
            ))

            # Get inserted ID
            cursor.execute("SELECT LAST_IDENTITY()")
            entity_id = cursor.fetchone()[0]
            entity_ids[(entity['text'], entity['type'])] = entity_id

        # Extract and store relationships (simplified version)
        relationships = _extract_simple_relationships(entities, entity_ids, clinical_note)

        for rel in relationships:
            cursor.execute("""
                INSERT INTO RAG.EntityRelationships
                (SourceEntityID, TargetEntityID, RelationshipType, ResourceID, Confidence, ExtractedAt)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                rel['source_id'],
                rel['target_id'],
                rel['type'],
                resource_id,
                rel['confidence']
            ))

        # Commit
        conn.commit()
        cursor.close()
        conn.close()

        print(f"[TRIGGER] Extracted {len(entities)} entities, {len(relationships)} relationships for resource {resource_id}")

    except Exception as e:
        print(f"[TRIGGER ERROR] Failed to extract entities: {e}")
        import traceback
        traceback.print_exc()


def _extract_simple_relationships(entities, entity_ids, text):
    """Simple relationship extraction for trigger context."""
    import re
    relationships = []
    text_lower = text.lower()

    for i, source_entity in enumerate(entities):
        for j, target_entity in enumerate(entities):
            if i >= j:
                continue

            source_key = (source_entity['text'], source_entity['type'])
            target_key = (target_entity['text'], target_entity['type'])

            if source_key not in entity_ids or target_key not in entity_ids:
                continue

            # CO_OCCURS_WITH for symptoms
            if source_entity['type'] == 'SYMPTOM' and target_entity['type'] == 'SYMPTOM':
                pattern = f"{source_entity['text']}.{{0,30}}{target_entity['text']}"
                if re.search(pattern, text_lower, re.IGNORECASE):
                    relationships.append({
                        'source_id': entity_ids[source_key],
                        'target_id': entity_ids[target_key],
                        'type': 'CO_OCCURS_WITH',
                        'confidence': 0.75
                    })

    return relationships
