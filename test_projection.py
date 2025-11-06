#!/usr/bin/env python3
"""Test script to verify VectorSearchApp projection works"""

import iris
import pandas as pd

# Credentials
server_location = "localhost"
port_number = 32782
namespace = "DEMO"
user_name = "_SYSTEM"
password = "ISCDEMO"

print("Connecting to IRIS database...")
conn = iris.connect(server_location, port_number, namespace, user_name, password)
cursor = conn.cursor()

# Test query
sql = """SELECT
DocumentReferenceContentAttachmentData, DocumentReferenceSubjectReference
FROM VectorSearchApp.DocumentReference"""

print("Executing query...")
cursor.execute(sql)

print("Fetching results...")
result_set = cursor.fetchall()

# Create DataFrame
cols = ["ClinicalNotes", "Patient"]
df = pd.DataFrame(result_set, columns=cols)

print(f"\n✅ Success! Found {len(df)} clinical notes")
print("\nFirst few rows:")
print(df.head())

# Extract Patient IDs
df["PatientID"] = pd.to_numeric(df["Patient"].astype(str).str.strip("Patient/"))
print(f"\nPatient IDs: {sorted(df['PatientID'].unique())}")

# Close connection
cursor.close()
conn.close()
print("\n✅ Connection closed successfully")
