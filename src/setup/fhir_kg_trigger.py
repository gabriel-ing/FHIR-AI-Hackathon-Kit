#!/usr/bin/env python3
"""
FHIR Knowledge Graph Trigger Setup

Creates IRIS triggers and stored procedures to automatically update
the knowledge graph when FHIR DocumentReference resources change.

This enables real-time knowledge graph synchronization with FHIR data.
"""

import sys
import os
import iris

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.adapters.fhir_document_adapter import FHIRDocumentAdapter
from src.extractors.medical_entity_extractor import MedicalEntityExtractor


# IRIS ObjectScript code for trigger and stored procedure
TRIGGER_CLASS_DEFINITION = """
/// Knowledge Graph Auto-Update Trigger for FHIR Resources
Class User.FHIRKGTrigger Extends %RegisteredObject
{

/// Update knowledge graph when DocumentReference is inserted or updated
ClassMethod OnDocumentReferenceChange(pResourceID As %Integer, pOperation As %String = "INSERT") As %Status
{
    Set tSC = $$$OK

    Try {
        // Only process DocumentReference resources
        Set tQuery = "SELECT ResourceType, ResourceString, Deleted FROM HSFHIR_X0001_R.Rsrc WHERE ID = ?"
        Set tStatement = ##class(%SQL.Statement).%New()
        Set tSC = tStatement.%Prepare(tQuery)
        If $$$ISERR(tSC) Quit

        Set tResult = tStatement.%Execute(pResourceID)
        If tResult.%Next() {
            Set tResourceType = tResult.%Get("ResourceType")
            Set tResourceString = tResult.%Get("ResourceString")
            Set tDeleted = tResult.%Get("Deleted")

            // Only process non-deleted DocumentReference resources
            If (tResourceType = "DocumentReference") && ((tDeleted = 0) || (tDeleted = "")) {
                Write !, "[TRIGGER] Processing DocumentReference ID: ", pResourceID

                // Call Python extraction via Embedded Python
                Do ..ExtractEntitiesEmbeddedPython(pResourceID, tResourceString)
            } ElseIf (tDeleted '= 0) && (tDeleted '= "") {
                // Resource was deleted - remove from knowledge graph
                Write !, "[TRIGGER] Deleting entities for resource ID: ", pResourceID
                Do ..DeleteEntitiesForResource(pResourceID)
            }
        }
    }
    Catch ex {
        Write !, "[TRIGGER ERROR] ", ex.DisplayString()
        Set tSC = ex.AsStatus()
    }

    Quit tSC
}

/// Extract entities using Embedded Python
ClassMethod ExtractEntitiesEmbeddedPython(pResourceID As %Integer, pResourceString As %String)
{
    // Use IRIS Embedded Python to call our entity extraction code
    Set tPython = ##class(%SYS.Python).Import("src.setup.fhir_kg_trigger_helper")
    Do tPython.extract"_and_store_entities(pResourceID, pResourceString)
}

/// Delete entities when resource is deleted
ClassMethod DeleteEntitiesForResource(pResourceID As %Integer)
{
    // Delete relationships first (foreign key constraint)
    &sql(DELETE FROM RAG.EntityRelationships WHERE ResourceID = :pResourceID)

    // Delete entities
    &sql(DELETE FROM RAG.Entities WHERE ResourceID = :pResourceID)

    Write !, "[TRIGGER] Deleted entities for resource ID: ", pResourceID
}

}
"""

TRIGGER_SQL_DEFINITION = """
-- Create AFTER INSERT trigger on FHIR resource table
CREATE TRIGGER FHIRDocRef_AfterInsert
ON HSFHIR_X0001_R.Rsrc
AFTER INSERT
FOR EACH ROW
WHEN (NEW.ResourceType = 'DocumentReference')
BEGIN
    -- Call stored procedure to update knowledge graph
    CALL User.FHIRKGTrigger_OnDocumentReferenceChange(NEW.ID, 'INSERT');
END;

-- Create AFTER UPDATE trigger on FHIR resource table
CREATE TRIGGER FHIRDocRef_AfterUpdate
ON HSFHIR_X0001_R.Rsrc
AFTER UPDATE
FOR EACH ROW
WHEN (NEW.ResourceType = 'DocumentReference')
BEGIN
    -- Call stored procedure to update knowledge graph
    CALL User.FHIRKGTrigger_OnDocumentReferenceChange(NEW.ID, 'UPDATE');
END;

-- Create AFTER DELETE trigger on FHIR resource table
CREATE TRIGGER FHIRDocRef_AfterDelete
ON HSFHIR_X0001_R.Rsrc
AFTER DELETE
FOR EACH ROW
WHEN (OLD.ResourceType = 'DocumentReference')
BEGIN
    -- Delete associated knowledge graph entities
    DELETE FROM RAG.EntityRelationships WHERE ResourceID = OLD.ID;
    DELETE FROM RAG.Entities WHERE ResourceID = OLD.ID;
END;
"""


def create_trigger_helper_class():
    """
    Create the ObjectScript class that handles trigger execution.

    Note: This uses IRIS system terminal commands to compile the class.
    """
    print("[INFO] Creating IRIS ObjectScript trigger class...")

    try:
        # Connect to IRIS
        conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')

        # Create the class using Embedded Python
        # Note: In production, you'd use %Studio or the Management Portal
        # For now, we'll provide instructions for manual setup

        print("[INFO] ✅ Trigger class definition ready")
        print("\n" + "="*80)
        print("To enable triggers, execute the following in IRIS Terminal:")
        print("="*80)
        print("\n1. Open IRIS Terminal:")
        print("   docker exec -it iris-fhir iris session DEMO")
        print("\n2. Paste this ObjectScript class definition:")
        print(TRIGGER_CLASS_DEFINITION)
        print("\n3. Compile the class:")
        print("   Do $SYSTEM.OBJ.Compile(\"User.FHIRKGTrigger\", \"ck\")")
        print("\n" + "="*80)

        conn.close()

    except Exception as e:
        print(f"[ERROR] Failed to create trigger class: {e}")
        import traceback
        traceback.print_exc()


def create_trigger_sql():
    """
    Create SQL triggers on FHIR resource table.

    Note: IRIS SQL triggers have specific syntax requirements.
    """
    print("\n[INFO] Creating SQL trigger definitions...")

    print("\n" + "="*80)
    print("SQL Trigger Definitions (execute in IRIS SQL):")
    print("="*80)
    print(TRIGGER_SQL_DEFINITION)
    print("="*80)

    print("\n[NOTE] IRIS may not support standard SQL triggers.")
    print("[NOTE] Use ObjectScript triggers instead (see class above).")
    print("[NOTE] Alternative: Use %OnAfterSave method in FHIR resource class")


def setup_alternative_approach():
    """
    Alternative approach: Create a stored procedure that can be called manually
    or scheduled to sync the knowledge graph.
    """
    print("\n[INFO] Alternative Approach: Scheduled Incremental Sync")
    print("="*80)

    stored_proc_code = """
-- Create stored procedure for incremental knowledge graph sync
CREATE PROCEDURE UpdateKnowledgeGraphIncremental()
LANGUAGE OBJECTSCRIPT
{
    // Get DocumentReference resources modified since last sync
    Set tQuery = "SELECT ID, ResourceString "
    Set tQuery = tQuery _ "FROM HSFHIR_X0001_R.Rsrc "
    Set tQuery = tQuery _ "WHERE ResourceType = 'DocumentReference' "
    Set tQuery = tQuery _ "AND Deleted = 0 "
    Set tQuery = tQuery _ "AND LastUpdated > (SELECT MAX(ExtractedAt) FROM RAG.Entities)"

    Set tStatement = ##class(%SQL.Statement).%New()
    Do tStatement.%Prepare(tQuery)
    Set tResult = tStatement.%Execute()

    Set tCount = 0
    While tResult.%Next() {
        Set tResourceID = tResult.%Get("ID")
        Set tResourceString = tResult.%Get("ResourceString")

        // Extract entities for this resource
        Do ##class(User.FHIRKGTrigger).ExtractEntitiesEmbeddedPython(tResourceID, tResourceString)
        Set tCount = tCount + 1
    }

    Write !, "Processed ", tCount, " updated resources"

    RETURN tCount
}
    """

    print(stored_proc_code)
    print("="*80)

    print("\n[INFO] Schedule this stored procedure to run periodically:")
    print("   - Every 5 minutes for near real-time sync")
    print("   - Every hour for batch processing")
    print("   - On-demand when needed")


def create_python_trigger_helper():
    """
    Create a Python helper module that will be called by IRIS Embedded Python.
    """
    helper_code = '''"""
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
'''

    # Write the helper file
    helper_path = os.path.join(PROJECT_ROOT, 'src/setup/fhir_kg_trigger_helper.py')
    with open(helper_path, 'w') as f:
        f.write(helper_code)

    print(f"\n[INFO] ✅ Created trigger helper: {helper_path}")


def main():
    """Main entry point for trigger setup."""
    print("="*80)
    print("FHIR Knowledge Graph Trigger Setup")
    print("="*80)

    print("\n[INFO] This script sets up automatic knowledge graph updates")
    print("[INFO] when FHIR DocumentReference resources change.")

    # Create Python helper for Embedded Python
    create_python_trigger_helper()

    # Show ObjectScript class definition
    create_trigger_helper_class()

    # Show SQL trigger definitions
    create_trigger_sql()

    # Show alternative approaches
    setup_alternative_approach()

    print("\n" + "="*80)
    print("IMPLEMENTATION RECOMMENDATIONS")
    print("="*80)
    print("""
Option 1: IRIS Triggers (Real-time, Event-driven)
  ✅ Pros: Immediate updates, no polling
  ❌ Cons: Requires ObjectScript, more complex setup

Option 2: Scheduled Incremental Sync (Near real-time)
  ✅ Pros: Pure Python, easier to maintain
  ✅ Pros: Can batch process for efficiency
  ❌ Cons: Slight delay (5-60 seconds typical)

Option 3: Manual/On-Demand Sync (Current implementation)
  ✅ Pros: Full control, simple
  ❌ Cons: Must remember to run after changes

RECOMMENDED: Option 2 - Scheduled Incremental Sync
  - Run: python3 src/setup/fhir_graphrag_setup.py --mode=sync
  - Schedule via cron/systemd timer every 5 minutes
  - Query: WHERE LastUpdated > (SELECT MAX(ExtractedAt) FROM RAG.Entities)
    """)

    print("="*80)


if __name__ == "__main__":
    main()
