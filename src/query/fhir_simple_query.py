#!/usr/bin/env python3
"""
FHIR GraphRAG Simple Query Interface (Text + Graph only)

Combines text keyword search and graph entity search without vector embeddings.
Useful when sentence-transformers/PyTorch is unavailable.

Usage:
    python3 src/query/fhir_simple_query.py "chest pain" --top-k 5
"""

import sys
import os
import time
import argparse
import yaml
import iris
import json
from typing import List, Dict, Any, Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.adapters.fhir_document_adapter import FHIRDocumentAdapter


class FHIRSimpleQuery:
    """Text + Graph search without vector embeddings."""

    def __init__(self, config_path: str = "config/fhir_graphrag_config.yaml"):
        self.config_path = config_path
        self.config = None
        self.connection = None
        self.cursor = None
        self.adapter = None
        self.rrf_k = 60  # RRF constant

    def load_config(self):
        """Load configuration."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            # Use defaults
            self.config = {
                'database': {
                    'iris': {
                        'host': 'localhost',
                        'port': 32782,
                        'namespace': 'DEMO',
                        'username': '_SYSTEM',
                        'password': 'ISCDEMO'
                    }
                }
            }

    def connect_database(self):
        """Connect to IRIS."""
        db_config = self.config['database']['iris']
        self.connection = iris.connect(
            db_config['host'],
            db_config['port'],
            db_config['namespace'],
            db_config['username'],
            db_config['password']
        )
        self.cursor = self.connection.cursor()
        print("[INFO] ✅ Connected to IRIS")

    def text_search(self, query: str, top_k: int = 30, patient_id: Optional[int] = None):
        """Text keyword search on decoded clinical notes."""
        print(f"[INFO] Text search: '{query}' (top_k={top_k})")

        keywords = query.lower().split()

        # Get all DocumentReference resources (decode and filter in Python)
        if patient_id:
            sql = """
                SELECT r.ID, r.ResourceString
                FROM HSFHIR_X0001_R.Rsrc r
                WHERE r.ResourceType = 'DocumentReference'
                AND r.Compartments LIKE ?
                AND (r.Deleted = 0 OR r.Deleted IS NULL)
            """
            self.cursor.execute(sql, [f'%Patient/{patient_id}%'])
        else:
            sql = """
                SELECT r.ID, r.ResourceString
                FROM HSFHIR_X0001_R.Rsrc r
                WHERE r.ResourceType = 'DocumentReference'
                AND (r.Deleted = 0 OR r.Deleted IS NULL)
            """
            self.cursor.execute(sql)

        results = []
        for row in self.cursor.fetchall():
            resource_id, resource_string = row

            try:
                # Parse FHIR JSON and extract decoded clinical note
                fhir_json = json.loads(resource_string)

                # Decode hex-encoded clinical note
                if "content" in fhir_json and len(fhir_json["content"]) > 0:
                    attachment = fhir_json["content"][0].get("attachment", {})
                    hex_data = attachment.get("data")
                    if hex_data:
                        clinical_note = bytes.fromhex(hex_data).decode('utf-8', errors='replace')
                        clinical_note_lower = clinical_note.lower()

                        # Count keyword matches in decoded text
                        score = sum(clinical_note_lower.count(kw) for kw in keywords)

                        if score > 0:
                            results.append({
                                'resource_id': resource_id,
                                'score': float(score),
                                'source': 'text',
                                'resource_string': resource_string
                            })
            except:
                # Skip documents that can't be decoded
                continue

        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:top_k]
        print(f"[INFO]   Found {len(results)} results")
        return results

    def graph_search(self, query: str, top_k: int = 10, patient_id: Optional[int] = None):
        """Graph entity search."""
        print(f"[INFO] Graph search: '{query}' (top_k={top_k})")

        keywords = query.lower().split()
        entity_clauses = [f"LOWER(EntityText) LIKE '%{kw}%'" for kw in keywords]
        entity_filter = " OR ".join(entity_clauses)

        sql = f"""
            SELECT DISTINCT e.ResourceID, COUNT(*) as EntityMatches, r.ResourceString
            FROM RAG.Entities e
            JOIN HSFHIR_X0001_R.Rsrc r ON e.ResourceID = r.ID
            WHERE ({entity_filter})
            AND r.ResourceType = 'DocumentReference'
            AND (r.Deleted = 0 OR r.Deleted IS NULL)
        """

        if patient_id:
            sql += f" AND r.Compartments LIKE '%Patient/{patient_id}%'"

        sql += " GROUP BY e.ResourceID, r.ResourceString ORDER BY EntityMatches DESC"

        self.cursor.execute(sql)

        results = []
        for row in self.cursor.fetchall()[:top_k]:
            resource_id, entity_matches, resource_string = row
            results.append({
                'resource_id': resource_id,
                'score': float(entity_matches),
                'source': 'graph',
                'resource_string': resource_string
            })

        print(f"[INFO]   Found {len(results)} results")
        return results

    def rrf_fusion(self, text_results, graph_results, top_k=5):
        """RRF fusion of text and graph results."""
        print(f"[INFO] Applying RRF fusion...")

        rrf_scores = {}
        resource_data = {}

        for rank, result in enumerate(text_results, start=1):
            rid = result['resource_id']
            score = 1.0 / (self.rrf_k + rank)
            if rid not in rrf_scores:
                rrf_scores[rid] = {'text': 0.0, 'graph': 0.0, 'total': 0.0}
                resource_data[rid] = result['resource_string']
            rrf_scores[rid]['text'] = score
            rrf_scores[rid]['total'] += score

        for rank, result in enumerate(graph_results, start=1):
            rid = result['resource_id']
            score = 1.0 / (self.rrf_k + rank)
            if rid not in rrf_scores:
                rrf_scores[rid] = {'text': 0.0, 'graph': 0.0, 'total': 0.0}
                resource_data[rid] = result['resource_string']
            rrf_scores[rid]['graph'] = score
            rrf_scores[rid]['total'] += score

        fused = []
        for rid, scores in sorted(rrf_scores.items(), key=lambda x: x[1]['total'], reverse=True)[:top_k]:
            fused.append({
                'resource_id': rid,
                'rrf_score': scores['total'],
                'text_score': scores['text'],
                'graph_score': scores['graph'],
                'resource_string': resource_data[rid]
            })

        print(f"[INFO]   Fused to {len(fused)} results")
        return fused

    def get_entities(self, resource_id):
        """Get entities for document."""
        sql = "SELECT EntityText, EntityType, Confidence FROM RAG.Entities WHERE ResourceID = ? ORDER BY Confidence DESC"
        self.cursor.execute(sql, [resource_id])
        return [{'text': r[0], 'type': r[1], 'conf': float(r[2])} for r in self.cursor.fetchall()]

    def display_results(self, query, results, execution_time):
        """Display results."""
        print("\n" + "="*80)
        print("FHIR GraphRAG Search Results (Text + Graph)")
        print("="*80)
        print(f"Query: \"{query}\"")
        print(f"Time: {execution_time:.3f}s")
        print(f"Results: {len(results)}")
        print("="*80)

        self.adapter = FHIRDocumentAdapter(self.connection)

        for idx, result in enumerate(results, 1):
            print(f"\n[{idx}] Document ID: {result['resource_id']}")
            print(f"    RRF Score: {result['rrf_score']:.4f}")
            print(f"      Text:  {result['text_score']:.4f}")
            print(f"      Graph: {result['graph_score']:.4f}")

            try:
                fhir_json = json.loads(result['resource_string'])
                note = self.adapter.extract_clinical_note(fhir_json)

                if note:
                    preview = note[:200] + "..." if len(note) > 200 else note
                    print(f"    Note: {preview}")
                else:
                    print(f"    Note: [No clinical note found]")

                entities = self.get_entities(result['resource_id'])
                if entities:
                    print(f"    Entities ({len(entities)}):")
                    for e in entities[:5]:
                        print(f"      - {e['text']} ({e['type']}, {e['conf']:.2f})")
            except Exception as e:
                print(f"    [Error displaying result: {e}]")

        print("\n" + "="*80)

    def query(self, query_text, patient_id=None, top_k=5, text_k=30, graph_k=10):
        """Execute search."""
        start = time.time()

        print(f"\n[INFO] ===== Search: \"{query_text}\" =====")

        text_results = self.text_search(query_text, top_k=text_k, patient_id=patient_id)
        graph_results = self.graph_search(query_text, top_k=graph_k, patient_id=patient_id)

        if not text_results and not graph_results:
            print("[WARN] No results found")
            return []

        fused = self.rrf_fusion(text_results, graph_results, top_k=top_k)

        exec_time = time.time() - start
        self.display_results(query_text, fused, exec_time)

        return fused

    def cleanup(self):
        """Cleanup."""
        if self.adapter:
            self.adapter.close()
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


def main():
    parser = argparse.ArgumentParser(description="FHIR Simple Search (Text + Graph)")
    parser.add_argument('query', help="Search query")
    parser.add_argument('--patient', type=int, help="Patient ID filter")
    parser.add_argument('--top-k', type=int, default=5, help="Results (default: 5)")
    parser.add_argument('--text-k', type=int, default=30, help="Text results (default: 30)")
    parser.add_argument('--graph-k', type=int, default=10, help="Graph results (default: 10)")
    parser.add_argument('--config', default='config/fhir_graphrag_config.yaml', help="Config")

    args = parser.parse_args()

    q = FHIRSimpleQuery(config_path=args.config)

    try:
        q.load_config()
        q.connect_database()

        # Check KG populated
        q.cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        count = q.cursor.fetchone()[0]
        if count == 0:
            print("[ERROR] Knowledge graph empty! Run: python3 src/setup/fhir_graphrag_setup.py --mode=build")
            sys.exit(1)

        print(f"[INFO] Knowledge graph: {count} entities")

        q.query(args.query, patient_id=args.patient, top_k=args.top_k, text_k=args.text_k, graph_k=args.graph_k)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        q.cleanup()


if __name__ == "__main__":
    main()
