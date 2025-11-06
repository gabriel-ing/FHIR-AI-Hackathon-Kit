#!/usr/bin/env python3
"""
Tutorial 3: Vector Search and LLM Prompting
Following the steps from 3-Vector-Search-LLM-Prompting.ipynb
"""

import sys
sys.path.insert(0, '/Users/tdyar/ws/FHIR-AI-Hackathon-Kit/Tutorial')

from Utils.get_iris_connection import get_cursor
from sentence_transformers import SentenceTransformer
from ollama import chat, ChatResponse

print("=" * 70)
print("Tutorial 3: Vector Search and LLM Prompting")
print("=" * 70)

# Step 1: Initialize
print("\n[Step 1] Initializing cursor and embedding model...")
cursor = get_cursor()
model = SentenceTransformer('all-MiniLM-L6-v2')
table_name = "VectorSearch.DocRefVectors"
print("✅ Initialization complete")

# Step 2: Vector Search
print("\n[Step 2] Testing vector search...")
query = "Has the patient reported any chest or respiratory complaints?"
print(f"Query: '{query}'")

query_vector = model.encode(query, normalize_embeddings=True, show_progress_bar=False).tolist()

search_sql = f"""
    SELECT TOP 3 ClinicalNotes
    FROM {table_name}
    WHERE PatientID = ?
    ORDER BY VECTOR_COSINE(NotesVector, TO_VECTOR(?,double)) DESC
"""

patient_id = 3
cursor.execute(search_sql, [patient_id, str(query_vector)])
results = cursor.fetchall()

print(f"✅ Found {len(results)} relevant clinical notes for Patient {patient_id}")
print("\nTop result (first 200 chars):")
print(results[0][0][:200] + "...\n")

# Step 3: Create vector search function
print("[Step 3] Creating reusable vector_search function...")

def vector_search(user_prompt, patient):
    """Search for relevant clinical notes using vector similarity"""
    search_vector = model.encode(user_prompt, normalize_embeddings=True, show_progress_bar=False).tolist()

    search_sql = f"""
        SELECT TOP 3 ClinicalNotes
        FROM {table_name}
        WHERE PatientID = {patient}
        ORDER BY VECTOR_COSINE(NotesVector, TO_VECTOR(?,double)) DESC
    """
    cursor.execute(search_sql, [str(search_vector)])
    return cursor.fetchall()

print("✅ vector_search function created")

# Step 4: Test LLM with Ollama
print("\n[Step 4] Testing LLM prompting with Ollama (gemma3:4b)...")
print("(This will take a moment to generate a response...)")

response: ChatResponse = chat(
    model='gemma3:4b',
    messages=[
        {
            'role': 'system',
            'content': (
                "You are a helpful and knowledgeable assistant designed to help a doctor interpret a patient's medical history "
                "using retrieved information from a database. Please provide a detailed and medically relevant explanation, "
                "include relevant dates, and ensure your response is coherent."
            )
        },
        {
            'role': 'user',
            'content': f"CONTEXT:\n{results}\n\nUSER QUESTION:\n{query}"
        }
    ]
)

print("\n" + "=" * 70)
print("LLM RESPONSE:")
print("=" * 70)
print(response['message']['content'])
print("=" * 70)

# Step 5: Test with different query
print("\n[Step 5] Testing with a different query...")
query2 = "Has the patient reported having bad headaches?"
results2 = vector_search(query2, patient_id)

print(f"Query: '{query2}'")
print(f"✅ Found {len(results2)} relevant notes")

response2: ChatResponse = chat(
    model='gemma3:4b',
    messages=[
        {
            'role': 'system',
            'content': (
                "You are a helpful and knowledgeable assistant designed to help a doctor interpret a patient's medical history "
                "using retrieved information from a database. Please provide a detailed and medically relevant explanation, "
                "include relevant dates, and ensure your response is coherent."
            )
        },
        {
            'role': 'user',
            'content': f"CONTEXT:\n{results2}\n\nUSER QUESTION:\n{query2}"
        }
    ]
)

print("\n" + "=" * 70)
print("LLM RESPONSE:")
print("=" * 70)
print(response2['message']['content'])
print("=" * 70)

print("\n" + "=" * 70)
print("✅ Tutorial 3 Core Functionality Complete!")
print("=" * 70)
print("\nSuccessfully tested:")
print("- ✅ Vector search with IRIS VECTOR_COSINE")
print("- ✅ Semantic similarity matching")
print("- ✅ LLM prompting with context (RAG)")
print("- ✅ Medical history interpretation")
print("\nNote: The notebook also demonstrates:")
print("- LangChain integration for conversation memory")
print("- Interactive RAGChatbot class")
print("- You can explore these features in the full notebook!")
print("=" * 70)
