#!/usr/bin/env python3
"""
Tutorial 2: Creating a Vector Database
Following the steps from 2-Creating-Vector-DB.ipynb
"""

import sys
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/Tutorial')

from Utils.get_iris_connection import get_cursor
import pandas as pd
import time
from sentence_transformers import SentenceTransformer

print("=" * 60)
print("Tutorial 2: Creating a Vector Database")
print("=" * 60)

# Step 1: Get cursor and fetch data
print("\n[Step 1] Connecting to IRIS and fetching data...")
cursor = get_cursor()

sql = """SELECT
DocumentReferenceContentAttachmentData, DocumentReferenceSubjectReference
FROM VectorSearchApp.DocumentReference"""

cursor.execute(sql)
out = cursor.fetchall()

cols = ["ClinicalNotes", "Patient"]
df = pd.DataFrame(out, columns=cols)
df["PatientID"] = pd.to_numeric(df["Patient"].astype(str).str.strip("Patient/"))

print(f"✅ Fetched {len(df)} clinical notes from {len(df['PatientID'].unique())} patients")

# Step 2: Decode clinical notes
print("\n[Step 2] Decoding clinical notes from hex to plain text...")
df["NotesDecoded"] = df["ClinicalNotes"].apply(
    lambda x: bytes.fromhex(x).decode("utf-8", errors="replace")
)

print("✅ Clinical notes decoded")
print("\nExample note (first 200 chars):")
print(df["NotesDecoded"][0][:200] + "...")

# Step 3: Generate embeddings
print("\n[Step 3] Loading sentence transformer model and generating embeddings...")
print("(This may take a moment...)")

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(df['NotesDecoded'].tolist(), normalize_embeddings=True)
df['Notes_Vector'] = embeddings.tolist()

print(f"✅ Generated {len(embeddings)} embeddings with {len(embeddings[0])} dimensions")

# Step 4: Create table
print("\n[Step 4] Creating vector table in IRIS...")
table_name = "VectorSearch.DocRefVectors"

# Drop table if it exists
try:
    cursor.execute(f"DROP TABLE {table_name}")
    print(f"  Dropped existing table {table_name}")
except:
    print(f"  No existing table to drop")

create_table_query = f"""
CREATE TABLE {table_name} (
PatientID INTEGER,
ClinicalNotes LONGVARCHAR,
NotesVector VECTOR(DOUBLE, 384)
)
"""

cursor.execute(create_table_query)
print(f"✅ Created table {table_name}")

# Step 5: Insert data (using the faster executemany method)
print("\n[Step 5] Inserting data into vector table...")
insert_query = f"INSERT INTO {table_name} (PatientID, ClinicalNotes, NotesVector) VALUES (?, ?, TO_VECTOR(?))"

st = time.time()
df["Notes_Vector_str"] = df["Notes_Vector"].astype(str)
rows_list = df[["PatientID", "NotesDecoded", "Notes_Vector_str"]].values.tolist()

cursor.executemany(insert_query, rows_list)
elapsed = time.time() - st
print(f"✅ Inserted {len(rows_list)} rows in {elapsed:.3f} seconds")

# Step 6: Verify data
print("\n[Step 6] Verifying data in table...")
sql_query = f"SELECT TOP 3 * FROM {table_name}"
cursor.execute(sql_query)
results = cursor.fetchall()
results_df = pd.DataFrame(results, columns=["PatientID", "NotesDecoded", "Notes_Vector"])

print(f"✅ Table contains data. Sample rows:")
print(results_df[["PatientID"]].head())
print(f"\nFirst vector (first 100 chars): {results_df['Notes_Vector'][0][:100]}...")

print("\n" + "=" * 60)
print("✅ Tutorial 2 Complete!")
print("=" * 60)
print(f"\nVector database created: {table_name}")
print(f"- {len(df)} clinical notes vectorized")
print(f"- {len(df['PatientID'].unique())} unique patients")
print(f"- 384-dimensional vectors")
print("\nReady for Tutorial 3: Vector Search & LLM Prompting!")
