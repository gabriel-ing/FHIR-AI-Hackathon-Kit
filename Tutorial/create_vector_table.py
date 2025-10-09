from Utils.get_iris_connection import get_cursor
import pandas as pd
from sentence_transformers import SentenceTransformer


if __name__=="__main__":
    cursor = get_cursor()

    sql = """SELECT 
    DocumentReferenceContentAttachmentData, DocumentReferenceSubjectReference
    FROM VectorSearchApp.DocumentReference"""

    cursor.execute(sql)
    out = cursor.fetchall()

    cols = ["ClinicalNotes", "Patient"] 

    df = pd.DataFrame(out, columns=cols)
    df["PatientID"] = pd.to_numeric(df["Patient"].astype(str).str.strip("Patient/"))
    df["NotesDecoded"] = df["ClinicalNotes"].apply(lambda x: bytes.fromhex(x).decode("utf-8", errors="replace"))

    model = SentenceTransformer('all-MiniLM-L6-v2') 

    # Generate embeddings for all descriptions at once. Batch processing makes it faster
    embeddings = model.encode(df['NotesDecoded'].tolist(), normalize_embeddings=True)

    # Add the embeddings to the DataFrame
    df['Notes_Vector'] = embeddings.tolist()

    table_name = "VectorSearch.DocRefVectors"

    create_table_query = f"""
    CREATE TABLE {table_name} (
    PatientID INTEGER,
    ClinicalNotes LONGVARCHAR,
    NotesVector VECTOR(DOUBLE, 384)
    )
    """

    cursor.execute(create_table_query)

    insert_query = f"INSERT INTO {table_name} ( PatientID, ClinicalNotes, NotesVector) values (?, ?, TO_VECTOR(?))"

    df["Notes_Vector_str"] = df["Notes_Vector"].astype(str)
    rows_list = df[["PatientID", "NotesDecoded", "Notes_Vector_str"]].values.tolist()

    cursor.executemany(insert_query, rows_list)