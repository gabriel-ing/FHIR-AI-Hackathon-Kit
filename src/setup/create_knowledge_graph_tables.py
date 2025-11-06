#!/usr/bin/env python3
"""
Create Knowledge Graph Tables for FHIR GraphRAG

This script creates the RAG.Entities and RAG.EntityRelationships tables
required for the GraphRAG knowledge graph implementation.

Tables created:
- RAG.Entities: Medical entity storage with embeddings
- RAG.EntityRelationships: Entity relationship storage with confidence scores

Usage:
    python3 src/setup/create_knowledge_graph_tables.py
"""

import sys
import iris

# Database connection settings
IRIS_HOST = 'localhost'
IRIS_PORT = 32782
IRIS_NAMESPACE = 'DEMO'
IRIS_USERNAME = '_SYSTEM'
IRIS_PASSWORD = 'ISCDEMO'


# DDL for RAG.Entities table (from contracts/entity-schema.json)
# Note: IRIS has native VECTOR type support - use VECTOR(DOUBLE, 384)
# Note: CHECK constraints omitted (IRIS DDL limitation)
CREATE_ENTITIES_TABLE = """
CREATE TABLE RAG.Entities (
  EntityID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  EntityText VARCHAR(500) NOT NULL,
  EntityType VARCHAR(50) NOT NULL,
  ResourceID BIGINT NOT NULL,
  Confidence FLOAT NOT NULL,
  EmbeddingVector VECTOR(DOUBLE, 384),
  ExtractedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ExtractedBy VARCHAR(100) DEFAULT 'hybrid'
)
"""

# Indexes for RAG.Entities
# Note: Vector index syntax TBD - skipping for now, can add later with correct IRIS syntax
CREATE_ENTITIES_INDEXES = [
    "CREATE INDEX idx_entities_type ON RAG.Entities(EntityType)",
    "CREATE INDEX idx_entities_confidence ON RAG.Entities(Confidence)",
    "CREATE INDEX idx_entities_resource ON RAG.Entities(ResourceID)"
    # Vector index on EmbeddingVector to be added once correct IRIS syntax is determined
]

# DDL for RAG.EntityRelationships table (from contracts/relationship-schema.json)
# Note: IRIS doesn't support CHECK constraints in CREATE TABLE, so they are omitted
CREATE_RELATIONSHIPS_TABLE = """
CREATE TABLE RAG.EntityRelationships (
  RelationshipID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  SourceEntityID BIGINT NOT NULL,
  TargetEntityID BIGINT NOT NULL,
  RelationshipType VARCHAR(50) NOT NULL,
  ResourceID BIGINT NOT NULL,
  Confidence FLOAT NOT NULL,
  ExtractedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  Context VARCHAR(1000)
)
"""

# Indexes for RAG.EntityRelationships
CREATE_RELATIONSHIPS_INDEXES = [
    "CREATE INDEX idx_relationships_type ON RAG.EntityRelationships(RelationshipType)",
    "CREATE INDEX idx_relationships_source ON RAG.EntityRelationships(SourceEntityID)",
    "CREATE INDEX idx_relationships_target ON RAG.EntityRelationships(TargetEntityID)",
    "CREATE INDEX idx_relationships_source_type ON RAG.EntityRelationships(SourceEntityID, RelationshipType)"
]


def create_tables():
    """Create knowledge graph tables and indexes."""
    try:
        # Connect to IRIS database
        print(f"[INFO] Connecting to IRIS database at {IRIS_HOST}:{IRIS_PORT}, namespace {IRIS_NAMESPACE}...")
        conn = iris.connect(IRIS_HOST, IRIS_PORT, IRIS_NAMESPACE, IRIS_USERNAME, IRIS_PASSWORD)
        cursor = conn.cursor()

        # Drop existing tables if they exist (for clean setup)
        print("[INFO] Dropping existing tables if they exist...")
        try:
            cursor.execute("DROP TABLE IF EXISTS RAG.EntityRelationships")
            cursor.execute("DROP TABLE IF EXISTS RAG.Entities")
            print("[INFO] ✅ Existing tables dropped")
        except Exception as e:
            print(f"[WARN] Could not drop tables (may not exist): {e}")

        # Create RAG.Entities table
        print("[INFO] Creating RAG.Entities table...")
        cursor.execute(CREATE_ENTITIES_TABLE)
        print("[INFO] ✅ Created table RAG.Entities")

        # Create indexes for RAG.Entities
        print("[INFO] Creating indexes on RAG.Entities...")
        for idx_sql in CREATE_ENTITIES_INDEXES:
            cursor.execute(idx_sql)
        print("[INFO] ✅ Created indexes on RAG.Entities")

        # Create RAG.EntityRelationships table
        print("[INFO] Creating RAG.EntityRelationships table...")
        cursor.execute(CREATE_RELATIONSHIPS_TABLE)
        print("[INFO] ✅ Created table RAG.EntityRelationships")

        # Create indexes for RAG.EntityRelationships
        print("[INFO] Creating indexes on RAG.EntityRelationships...")
        for idx_sql in CREATE_RELATIONSHIPS_INDEXES:
            cursor.execute(idx_sql)
        print("[INFO] ✅ Created indexes on RAG.EntityRelationships")

        # Commit changes
        conn.commit()

        # Verify table creation
        print("\n[INFO] Verifying table creation...")
        cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        entities_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM RAG.EntityRelationships")
        relationships_count = cursor.fetchone()[0]

        print(f"[INFO] ✅ RAG.Entities table verified (current rows: {entities_count})")
        print(f"[INFO] ✅ RAG.EntityRelationships table verified (current rows: {relationships_count})")

        # Close connection
        cursor.close()
        conn.close()

        print("\n[INFO] ===== Knowledge Graph Tables Created Successfully =====")
        print("[INFO] Tables:")
        print("[INFO]   - RAG.Entities")
        print("[INFO]   - RAG.EntityRelationships")
        print("[INFO] Initialization complete!")

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to create knowledge graph tables: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
