#!/usr/bin/env python3
"""
Direct FHIR Vector Integration - Proof of Concept
Adds vector search capability directly to FHIR native tables
"""

import sys
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/Tutorial')

import iris
import json
from sentence_transformers import SentenceTransformer

print("=" * 80)
print("Direct FHIR Vector Integration - Proof of Concept")
print("=" * 80)

# Connect to IRIS
conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
cursor = conn.cursor()

# Step 1: Create companion vector table
print("\n[Step 1] Creating companion vector table...")
table_name = "VectorSearch.FHIRResourceVectors"

try:
    cursor.execute(f"DROP TABLE {table_name}")
    print(f"  Dropped existing {table_name}")
except:
    print(f"  No existing table to drop")

create_sql = f"""
CREATE TABLE {table_name} (
    ResourceID BIGINT PRIMARY KEY,
    ResourceType VARCHAR(50),
    Vector VECTOR(DOUBLE, 384),
    VectorModel VARCHAR(100),
    LastUpdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""
cursor.execute(create_sql)
print(f"✅ Created {table_name}")

# Step 2: Extract and vectorize DocumentReference clinical notes
print("\n[Step 2] Extracting DocumentReference clinical notes from native FHIR table...")

extract_sql = """
SELECT ID, ResourceId, ResourceString
FROM HSFHIR_X0001_R.Rsrc
WHERE ResourceType = 'DocumentReference'
  AND Deleted = 0
"""

cursor.execute(extract_sql)
resources = cursor.fetchall()
print(f"✅ Found {len(resources)} DocumentReference resources")

# Step 3: Generate vectors
print("\n[Step 3] Generating vectors for clinical notes...")
model = SentenceTransformer('all-MiniLM-L6-v2')

vectors_to_insert = []
for id, resource_id, json_str in resources:
    try:
        data = json.loads(json_str)
        if 'content' in data and data['content']:
            encoded_data = data['content'][0]['attachment']['data']
            clinical_note = bytes.fromhex(encoded_data).decode('utf-8', errors='replace')

            # Generate vector
            vector = model.encode(clinical_note, normalize_embeddings=True, show_progress_bar=False)
            vectors_to_insert.append([
                id,
                'DocumentReference',
                str(vector.tolist()),
                'all-MiniLM-L6-v2'
            ])
    except Exception as e:
        print(f"  Warning: Failed to process resource {resource_id}: {e}")

print(f"✅ Generated {len(vectors_to_insert)} vectors")

# Step 4: Insert vectors
print("\n[Step 4] Inserting vectors into companion table...")

insert_sql = f"""
INSERT INTO {table_name} (ResourceID, ResourceType, Vector, VectorModel)
VALUES (?, ?, TO_VECTOR(?), ?)
"""

cursor.executemany(insert_sql, vectors_to_insert)
print(f"✅ Inserted {len(vectors_to_insert)} vectors")

# Step 5: Test vector search with JOIN
print("\n[Step 5] Testing vector search with JOIN to native FHIR table...")

test_query = "Has the patient reported any chest or respiratory complaints?"
test_vector = model.encode(test_query, normalize_embeddings=True, show_progress_bar=False)

search_sql = f"""
SELECT TOP 3
    r.ResourceId,
    r.ResourceString
FROM HSFHIR_X0001_R.Rsrc r
INNER JOIN {table_name} v ON r.ID = v.ResourceID
WHERE r.ResourceType = 'DocumentReference'
  AND r.Deleted = 0
  AND r.Compartments LIKE '%Patient/3%'
ORDER BY VECTOR_COSINE(v.Vector, TO_VECTOR(?, double)) DESC
"""

cursor.execute(search_sql, [str(test_vector.tolist())])
results = cursor.fetchall()

print(f"\nQuery: '{test_query}'")
print(f"✅ Found {len(results)} relevant clinical notes")

for i, (resource_id, json_str) in enumerate(results, 1):
    data = json.loads(json_str)
    encoded_data = data['content'][0]['attachment']['data']
    clinical_note = bytes.fromhex(encoded_data).decode('utf-8', errors='replace')

    print(f"\nResult {i} - Resource: {resource_id}")
    print("-" * 80)
    print(clinical_note[:200] + "...")

print("\n" + "=" * 80)
print("✅ Proof of Concept Complete!")
print("=" * 80)
print("\nSuccessfully demonstrated:")
print("- ✅ Direct access to FHIR native storage (HSFHIR_X0001_R.Rsrc)")
print("- ✅ Companion vector table without modifying FHIR schema")
print("- ✅ Vector search with JOIN to native FHIR resources")
print("- ✅ No SQL Builder configuration required!")
print("\nThis approach:")
print("- Keeps vectors alongside FHIR data")
print("- Works with any FHIR resource type")
print("- Doesn't modify core FHIR tables")
print("- Can be automated with triggers/methods")
print("=" * 80)
