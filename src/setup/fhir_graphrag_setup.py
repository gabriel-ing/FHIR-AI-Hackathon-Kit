#!/usr/bin/env python3
"""
FHIR GraphRAG Setup Script

Builds the knowledge graph by extracting medical entities and relationships
from FHIR DocumentReference resources.

Modes:
- init: Create knowledge graph tables
- build: Extract entities and relationships, populate knowledge graph
- stats: Display knowledge graph statistics

Usage:
    python3 src/setup/fhir_graphrag_setup.py --mode=init
    python3 src/setup/fhir_graphrag_setup.py --mode=build
    python3 src/setup/fhir_graphrag_setup.py --mode=stats
"""

import sys
import os
import time
import argparse
import yaml
import iris
from datetime import datetime

# Add rag-templates to Python path
RAG_TEMPLATES_PATH = "/Users/tdyar/ws/rag-templates"
if RAG_TEMPLATES_PATH not in sys.path:
    sys.path.insert(0, RAG_TEMPLATES_PATH)

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import adapters and extractors
from src.adapters.fhir_document_adapter import FHIRDocumentAdapter
from src.extractors.medical_entity_extractor import MedicalEntityExtractor


class FHIRGraphRAGSetup:
    """
    Setup and build FHIR GraphRAG knowledge graph.

    Orchestrates entity extraction, relationship mapping, and knowledge graph population.
    """

    def __init__(self, config_path: str = "config/fhir_graphrag_config.yaml"):
        """
        Initialize GraphRAG setup.

        Args:
            config_path: Path to BYOT configuration file
        """
        self.config_path = config_path
        self.config = None
        self.connection = None
        self.cursor = None
        self.adapter = None
        self.extractor = None

        # Statistics
        self.stats = {
            'total_documents': 0,
            'total_entities': 0,
            'total_relationships': 0,
            'processing_time': 0.0,
            'entities_by_type': {},
            'relationships_by_type': {},
        }

    def load_config(self):
        """
        Load BYOT configuration from YAML file.

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config is invalid YAML
        """
        print(f"[INFO] Loading FHIR GraphRAG configuration from {self.config_path}...")

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        print("[INFO] ✅ Configuration loaded successfully")

        # Validate required configuration sections
        required_sections = ['database', 'pipelines']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required config section: {section}")

    def connect_database(self):
        """
        Connect to IRIS database using configuration.

        Raises:
            ConnectionError: If database connection fails
        """
        try:
            db_config = self.config['database']['iris']

            host = db_config.get('host', 'localhost')
            port = db_config.get('port', 32782)
            namespace = db_config.get('namespace', 'DEMO')
            username = db_config.get('username', '_SYSTEM')
            password = db_config.get('password', 'ISCDEMO')

            print(f"[INFO] Connecting to IRIS database at {host}:{port}, namespace {namespace}...")

            self.connection = iris.connect(host, port, namespace, username, password)
            self.cursor = self.connection.cursor()

            print("[INFO] ✅ Connected to IRIS database")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to IRIS database: {e}")

    def init_tables(self):
        """
        Initialize knowledge graph tables (mode=init).

        Delegates to create_knowledge_graph_tables.py script.
        """
        print("[INFO] Initializing GraphRAG knowledge graph tables...")

        # Import and run table creation
        from src.setup.create_knowledge_graph_tables import create_tables

        success = create_tables()

        if not success:
            raise RuntimeError("Failed to create knowledge graph tables")

        print("[INFO] ✅ Knowledge graph tables initialized")

    def build_knowledge_graph(self):
        """
        Build knowledge graph by extracting entities and relationships (mode=build).

        This is the main entity extraction pipeline.
        """
        print("[INFO] ===== Building FHIR GraphRAG Knowledge Graph =====")

        start_time = time.time()

        # Load configuration
        self.load_config()

        # Connect to database
        self.connect_database()

        # Initialize components
        print("[INFO] Initializing components...")
        self.adapter = FHIRDocumentAdapter(self.connection)

        pipeline_config = self.config.get('pipelines', {}).get('graphrag', {})
        min_confidence = pipeline_config.get('min_entity_confidence', 0.7)

        self.extractor = MedicalEntityExtractor(min_confidence=min_confidence)
        print(f"[INFO] ✅ Components initialized (min_confidence={min_confidence})")

        # Load FHIR documents
        print("[INFO] Loading FHIR DocumentReference resources...")
        documents = self.adapter.load_fhir_documents(resource_type="DocumentReference")
        self.stats['total_documents'] = len(documents)

        if not documents:
            print("[WARN] No documents found to process")
            return

        print(f"[INFO] ✅ Loaded {len(documents)} DocumentReference resources")

        # Process each document
        for idx, document in enumerate(documents, 1):
            print(f"[INFO] Processing document {idx}/{len(documents)} (ID: {document['id']})...")

            doc_start = time.time()

            # Extract entities
            entities = self.extractor.extract_entities(document['text'])

            print(f"[INFO]   ✅ Extracted {len(entities)} entities")

            # Store entities in database
            entity_ids = self._store_entities(document['metadata']['resource_id'], entities)

            # Extract relationships
            relationships = self._extract_relationships(entities, entity_ids, document['text'])

            print(f"[INFO]   ✅ Identified {len(relationships)} relationships")

            # Store relationships in database
            self._store_relationships(document['metadata']['resource_id'], relationships)

            doc_time = time.time() - doc_start
            print(f"[INFO]   Processing time: {doc_time:.2f} seconds\n")

        # Calculate final statistics
        self.stats['processing_time'] = time.time() - start_time

        # Commit all changes
        self.connection.commit()

        # Display summary
        self._display_build_summary()

    def _store_entities(self, resource_id: int, entities: list) -> dict:
        """
        Store extracted entities in RAG.Entities table.

        Args:
            resource_id: FHIR resource ID
            entities: List of extracted entities

        Returns:
            Dict mapping (entity_text, entity_type) to EntityID
        """
        entity_ids = {}

        for entity in entities:
            try:
                # Insert entity
                self.cursor.execute("""
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
                self.cursor.execute("SELECT LAST_IDENTITY()")
                entity_id = self.cursor.fetchone()[0]

                # Map entity to ID
                entity_ids[(entity['text'], entity['type'])] = entity_id

                # Update statistics
                self.stats['total_entities'] += 1
                entity_type = entity['type']
                self.stats['entities_by_type'][entity_type] = \
                    self.stats['entities_by_type'].get(entity_type, 0) + 1

            except Exception as e:
                print(f"[WARN] Failed to store entity '{entity['text']}': {e}")

        return entity_ids

    def _extract_relationships(self, entities: list, entity_ids: dict, text: str) -> list:
        """
        Extract relationships between entities using simple heuristics.

        Args:
            entities: List of extracted entities
            entity_ids: Mapping of (entity_text, entity_type) to EntityID
            text: Original clinical note text

        Returns:
            List of relationships
        """
        relationships = []
        text_lower = text.lower()

        # Simple relationship extraction heuristics
        for i, source_entity in enumerate(entities):
            for j, target_entity in enumerate(entities):
                if i >= j:  # Avoid duplicates and self-loops
                    continue

                source_key = (source_entity['text'], source_entity['type'])
                target_key = (target_entity['text'], target_entity['type'])

                if source_key not in entity_ids or target_key not in entity_ids:
                    continue

                # TREATS relationship (MEDICATION -> CONDITION or SYMPTOM)
                if source_entity['type'] == 'MEDICATION' and \
                   target_entity['type'] in ('CONDITION', 'SYMPTOM'):
                    if self._check_treats_relationship(source_entity, target_entity, text_lower):
                        relationships.append({
                            'source_id': entity_ids[source_key],
                            'target_id': entity_ids[target_key],
                            'type': 'TREATS',
                            'confidence': 0.85
                        })

                # CAUSES relationship (CONDITION -> SYMPTOM)
                if source_entity['type'] == 'CONDITION' and \
                   target_entity['type'] == 'SYMPTOM':
                    if self._check_causes_relationship(source_entity, target_entity, text_lower):
                        relationships.append({
                            'source_id': entity_ids[source_key],
                            'target_id': entity_ids[target_key],
                            'type': 'CAUSES',
                            'confidence': 0.80
                        })

                # CO_OCCURS_WITH relationship (SYMPTOM <-> SYMPTOM)
                if source_entity['type'] == 'SYMPTOM' and \
                   target_entity['type'] == 'SYMPTOM':
                    if self._check_cooccurs_relationship(source_entity, target_entity, text_lower):
                        relationships.append({
                            'source_id': entity_ids[source_key],
                            'target_id': entity_ids[target_key],
                            'type': 'CO_OCCURS_WITH',
                            'confidence': 0.75
                        })

        return relationships

    def _check_treats_relationship(self, medication, condition, text):
        """Check if TREATS relationship exists using text proximity."""
        # Look for patterns like "prescribed X for Y", "X to treat Y"
        pattern = f"({medication['text']}.{{0,50}}{condition['text']}|{condition['text']}.{{0,50}}{medication['text']})"
        import re
        if re.search(pattern, text, re.IGNORECASE):
            if any(keyword in text for keyword in ['prescribed', 'treat', 'for']):
                return True
        return False

    def _check_causes_relationship(self, condition, symptom, text):
        """Check if CAUSES relationship exists using text proximity."""
        # Look for patterns like "X causes Y", "Y from X"
        pattern = f"{condition['text']}.{{0,50}}{symptom['text']}"
        import re
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _check_cooccurs_relationship(self, symptom1, symptom2, text):
        """Check if CO_OCCURS_WITH relationship exists using text proximity."""
        # Look for symptoms mentioned close together
        pattern = f"{symptom1['text']}.{{0,30}}{symptom2['text']}"
        import re
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _store_relationships(self, resource_id: int, relationships: list):
        """
        Store extracted relationships in RAG.EntityRelationships table.

        Args:
            resource_id: FHIR resource ID
            relationships: List of relationships to store
        """
        for rel in relationships:
            try:
                self.cursor.execute("""
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

                # Update statistics
                self.stats['total_relationships'] += 1
                rel_type = rel['type']
                self.stats['relationships_by_type'][rel_type] = \
                    self.stats['relationships_by_type'].get(rel_type, 0) + 1

            except Exception as e:
                print(f"[WARN] Failed to store relationship: {e}")

    def _display_build_summary(self):
        """Display knowledge graph build summary."""
        print("\n" + "="*80)
        print("===== Knowledge Graph Build Complete =====")
        print("="*80)
        print(f"Total documents processed: {self.stats['total_documents']}")
        print(f"Total entities extracted: {self.stats['total_entities']}")
        print(f"Total relationships identified: {self.stats['total_relationships']}")
        print(f"Processing time: {self.stats['processing_time']:.2f} seconds")
        print(f"Average time per document: {self.stats['processing_time'] / max(self.stats['total_documents'], 1):.2f} seconds")

        print("\nEntities by type:")
        for entity_type, count in sorted(self.stats['entities_by_type'].items()):
            print(f"  {entity_type:15} : {count:4}")

        print("\nRelationships by type:")
        for rel_type, count in sorted(self.stats['relationships_by_type'].items()):
            print(f"  {rel_type:15} : {count:4}")

        print("="*80)

    def incremental_sync(self):
        """
        Incremental knowledge graph sync - only process new/updated resources (mode=sync).

        This finds FHIR resources that have been updated since the last sync
        and extracts entities/relationships only for those resources.

        Ideal for scheduled/automated execution (e.g., cron job every 5 minutes).
        """
        print("[INFO] ===== Incremental Knowledge Graph Sync =====")

        start_time = time.time()

        # Load configuration and connect
        self.load_config()
        self.connect_database()

        # Initialize components
        print("[INFO] Initializing components...")
        self.adapter = FHIRDocumentAdapter(self.connection)

        pipeline_config = self.config.get('pipelines', {}).get('graphrag', {})
        min_confidence = pipeline_config.get('min_entity_confidence', 0.7)
        self.extractor = MedicalEntityExtractor(min_confidence=min_confidence)

        # Find last sync time from RAG.Entities
        print("[INFO] Checking for resources updated since last sync...")
        self.cursor.execute("SELECT MAX(ExtractedAt) FROM RAG.Entities")
        last_sync = self.cursor.fetchone()[0]

        if last_sync:
            print(f"[INFO] Last sync: {last_sync}")
            # Query FHIR resources updated since last sync
            query = """
                SELECT TOP 100 ID, ResourceType, ResourceString, Compartments, Deleted
                FROM HSFHIR_X0001_R.Rsrc
                WHERE ResourceType = 'DocumentReference'
                AND (Deleted = 0 OR Deleted IS NULL)
                AND LastModified > ?
            """
            self.cursor.execute(query, [last_sync])
        else:
            print("[INFO] No previous sync found - running initial sync")
            # No previous sync - get all resources
            query = """
                SELECT TOP 100 ID, ResourceType, ResourceString, Compartments, Deleted
                FROM HSFHIR_X0001_R.Rsrc
                WHERE ResourceType = 'DocumentReference'
                AND (Deleted = 0 OR Deleted IS NULL)
            """
            self.cursor.execute(query)

        rows = self.cursor.fetchall()

        if not rows:
            print("[INFO] ✅ No new or updated resources to process")
            print(f"[INFO] Sync completed in {time.time() - start_time:.2f} seconds")
            return

        print(f"[INFO] Found {len(rows)} resources to process")

        # Process each updated resource
        processed_count = 0
        for idx, row in enumerate(rows, 1):
            resource_id = row[0]
            resource_string = row[2]

            try:
                # Parse and convert to document
                import json
                fhir_json = json.loads(resource_string)

                # Extract clinical note
                clinical_note = self.adapter.extract_clinical_note(fhir_json)
                if not clinical_note:
                    continue

                print(f"[INFO] Processing resource {idx}/{len(rows)} (ID: {resource_id})...")

                # Delete existing entities/relationships for this resource (update scenario)
                self.cursor.execute("DELETE FROM RAG.EntityRelationships WHERE ResourceID = ?", [resource_id])
                self.cursor.execute("DELETE FROM RAG.Entities WHERE ResourceID = ?", [resource_id])

                # Extract entities
                entities = self.extractor.extract_entities(clinical_note)
                print(f"[INFO]   ✅ Extracted {len(entities)} entities")

                # Store entities
                entity_ids = self._store_entities(resource_id, entities)

                # Extract and store relationships
                relationships = self._extract_relationships(entities, entity_ids, clinical_note)
                self._store_relationships(resource_id, relationships)
                print(f"[INFO]   ✅ Identified {len(relationships)} relationships")

                processed_count += 1

            except Exception as e:
                print(f"[WARN] Failed to process resource {resource_id}: {e}")

        # Commit changes
        self.connection.commit()

        sync_time = time.time() - start_time
        print(f"\n[INFO] ===== Incremental Sync Complete =====")
        print(f"[INFO] Processed {processed_count} resources in {sync_time:.2f} seconds")
        print(f"[INFO] Average: {sync_time / max(processed_count, 1):.2f} seconds per resource")

    def display_stats(self):
        """
        Display knowledge graph statistics (mode=stats).
        """
        print("[INFO] ===== FHIR GraphRAG Knowledge Graph Statistics =====")

        # Connect to database
        self.load_config()
        self.connect_database()

        # Query entity statistics
        print("\nEntity Statistics:")
        self.cursor.execute("""
            SELECT EntityType, COUNT(*) as EntityCount, AVG(Confidence) as AvgConfidence
            FROM RAG.Entities
            GROUP BY EntityType
            ORDER BY EntityCount DESC
        """)

        for row in self.cursor.fetchall():
            entity_type, count, avg_conf = row
            print(f"  {entity_type:15} : {count:4} entities (avg confidence: {avg_conf:.3f})")

        # Query relationship statistics
        print("\nRelationship Statistics:")
        self.cursor.execute("""
            SELECT RelationshipType, COUNT(*) as RelCount, AVG(Confidence) as AvgConfidence
            FROM RAG.EntityRelationships
            GROUP BY RelationshipType
            ORDER BY RelCount DESC
        """)

        for row in self.cursor.fetchall():
            rel_type, count, avg_conf = row
            print(f"  {rel_type:15} : {count:4} relationships (avg confidence: {avg_conf:.3f})")

        # Query total counts
        self.cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        total_entities = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT COUNT(*) FROM RAG.EntityRelationships")
        total_relationships = self.cursor.fetchone()[0]

        print(f"\nTotal Entities: {total_entities}")
        print(f"Total Relationships: {total_relationships}")

        print("="*80)

    def cleanup(self):
        """Close database connections and cleanup resources."""
        if self.adapter:
            self.adapter.close()
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


def main():
    """Main entry point for GraphRAG setup script."""
    parser = argparse.ArgumentParser(description="FHIR GraphRAG Setup")
    parser.add_argument('--mode', choices=['init', 'build', 'sync', 'stats'], required=True,
                        help="Operation mode: init (create tables), build (full extract), sync (incremental), stats (display statistics)")
    parser.add_argument('--config', default='config/fhir_graphrag_config.yaml',
                        help="Path to configuration file")

    args = parser.parse_args()

    setup = FHIRGraphRAGSetup(config_path=args.config)

    try:
        if args.mode == 'init':
            setup.init_tables()

        elif args.mode == 'build':
            # Check rag-templates availability
            try:
                from iris_rag import create_pipeline
                print("[INFO] ✅ rag-templates library accessible")
            except ImportError:
                print("[ERROR] rag-templates library not found")
                print(f"[ERROR] Please ensure {RAG_TEMPLATES_PATH} exists and is accessible")
                sys.exit(1)

            setup.build_knowledge_graph()

        elif args.mode == 'sync':
            # Incremental sync - only process new/updated resources
            setup.incremental_sync()

        elif args.mode == 'stats':
            setup.display_stats()

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        setup.cleanup()


if __name__ == "__main__":
    main()
