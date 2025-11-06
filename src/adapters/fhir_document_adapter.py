"""
FHIR Document Adapter

Converts FHIR DocumentReference resources from IRIS native tables
to rag-templates Document format for GraphRAG processing.

This adapter implements BYOT (Bring Your Own Table) pattern by reading
directly from HSFHIR_X0001_R.Rsrc without modifying the source data.
"""

import json
from typing import List, Dict, Optional, Any
import iris


class FHIRDocumentAdapter:
    """
    Adapter for converting FHIR DocumentReference resources to rag-templates Documents.

    Implements zero-copy BYOT pattern for FHIR native tables.
    """

    def __init__(self, connection):
        """
        Initialize the FHIR document adapter.

        Args:
            connection: Active IRIS database connection
        """
        self.connection = connection
        self.cursor = connection.cursor()

    def extract_clinical_note(self, fhir_json: Dict[str, Any]) -> Optional[str]:
        """
        Extract and decode clinical note text from FHIR DocumentReference.

        FHIR stores document content as hex-encoded data in the content.attachment.data field.
        This method hex-decodes the clinical note text.

        Args:
            fhir_json: Parsed FHIR DocumentReference JSON

        Returns:
            Decoded clinical note text, or None if extraction fails

        Example FHIR structure:
            {
                "resourceType": "DocumentReference",
                "content": [{
                    "attachment": {
                        "contentType": "text/plain",
                        "data": "50617469656e74207265706f727473..."
                    }
                }]
            }
        """
        try:
            # Navigate FHIR structure to get hex-encoded content
            if "content" not in fhir_json or not fhir_json["content"]:
                return None

            attachment = fhir_json["content"][0].get("attachment", {})
            hex_data = attachment.get("data")

            if not hex_data:
                return None

            # Decode hex to get clinical note text
            clinical_note = bytes.fromhex(hex_data).decode('utf-8', errors='replace')

            return clinical_note

        except (KeyError, IndexError, ValueError, UnicodeDecodeError) as e:
            print(f"[WARN] Failed to extract clinical note: {e}")
            return None

    def fhir_row_to_document(self, row: tuple) -> Optional[Dict[str, Any]]:
        """
        Convert a FHIR table row to rag-templates Document format.

        Args:
            row: Database row from HSFHIR_X0001_R.Rsrc query
                 Expected columns: (ID, ResourceType, ResourceString, Compartments, Deleted)

        Returns:
            Document dict in rag-templates format, or None if conversion fails

        Document format:
            {
                "id": "resource-id",
                "text": "clinical note content",
                "metadata": {
                    "resource_id": 123,
                    "resource_type": "DocumentReference",
                    "patient_id": "Patient/3",
                    "source": "FHIR"
                }
            }
        """
        try:
            resource_id, resource_type, resource_string, compartments, deleted = row

            # Skip deleted resources
            if deleted:
                return None

            # Parse FHIR JSON from ResourceString
            # Note: IRIS stores FHIR as JSON string in ResourceString column
            fhir_json = json.loads(resource_string)

            # Extract clinical note text
            clinical_note = self.extract_clinical_note(fhir_json)
            if not clinical_note:
                return None

            # Extract patient ID from subject reference
            patient_id = None
            if "subject" in fhir_json and "reference" in fhir_json["subject"]:
                patient_id = fhir_json["subject"]["reference"]

            # Create rag-templates Document format
            document = {
                "id": f"{resource_type}-{resource_id}",
                "text": clinical_note,
                "metadata": {
                    "resource_id": resource_id,
                    "resource_type": resource_type,
                    "patient_id": patient_id,
                    "compartments": compartments,
                    "source": "FHIR"
                }
            }

            return document

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[WARN] Failed to convert FHIR row to document: {e}")
            return None

    def load_fhir_documents(
        self,
        resource_type: str = "DocumentReference",
        limit: Optional[int] = None,
        patient_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load FHIR documents from native tables and convert to rag-templates format.

        This is the main entry point for BYOT integration. It queries HSFHIR_X0001_R.Rsrc
        directly without modifying the source data.

        Args:
            resource_type: FHIR resource type to load (default: "DocumentReference")
            limit: Maximum number of documents to load (None for all)
            patient_id: Filter by patient ID (e.g., "Patient/3")

        Returns:
            List of documents in rag-templates format

        Example usage:
            adapter = FHIRDocumentAdapter(conn)
            documents = adapter.load_fhir_documents(limit=10)
            for doc in documents:
                print(doc["id"], doc["metadata"]["patient_id"])
        """
        try:
            # Build query with optional TOP clause
            top_clause = f"TOP {limit}" if limit else ""
            query = f"""
                SELECT {top_clause} ID, ResourceType, ResourceString, Compartments, Deleted
                FROM HSFHIR_X0001_R.Rsrc
                WHERE ResourceType = ?
                AND (Deleted = 0 OR Deleted IS NULL)
            """
            params = [resource_type]

            # Add patient filter if specified
            if patient_id:
                query += " AND Compartments LIKE ?"
                params.append(f"%{patient_id}%")

            # Execute query
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            print(f"[INFO] Loaded {len(rows)} {resource_type} resources from FHIR native table")

            # Convert rows to documents
            documents = []
            for row in rows:
                doc = self.fhir_row_to_document(row)
                if doc:
                    documents.append(doc)

            print(f"[INFO] Successfully converted {len(documents)} resources to documents")

            return documents

        except Exception as e:
            print(f"[ERROR] Failed to load FHIR documents: {e}")
            import traceback
            traceback.print_exc()
            return []

    def close(self):
        """Close the database cursor."""
        if self.cursor:
            self.cursor.close()


# Example usage
if __name__ == "__main__":
    # Connect to IRIS
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')

    # Create adapter
    adapter = FHIRDocumentAdapter(conn)

    # Load documents
    documents = adapter.load_fhir_documents(limit=5)

    # Display sample
    for doc in documents:
        print(f"\n{'='*80}")
        print(f"Document ID: {doc['id']}")
        print(f"Patient: {doc['metadata']['patient_id']}")
        print(f"Text preview: {doc['text'][:200]}...")

    # Cleanup
    adapter.close()
    conn.close()
