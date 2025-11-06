#!/usr/bin/env python3
"""
FHIR GraphRAG Query Interface

Multi-modal search combining:
- Vector similarity search (semantic search)
- Text keyword matching (BM25/full-text)
- Graph traversal (entity relationships)

Results are fused using RRF (Reciprocal Rank Fusion) for optimal ranking.

Usage:
    python3 src/query/fhir_graphrag_query.py "respiratory symptoms"
    python3 src/query/fhir_graphrag_query.py "medications for hypertension" --patient 5
    python3 src/query/fhir_graphrag_query.py --demo
"""

import sys
import os
import time
import argparse
import yaml
import iris
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Add rag-templates to path
RAG_TEMPLATES_PATH = "/Users/tdyar/ws/rag-templates"
if RAG_TEMPLATES_PATH not in sys.path:
    sys.path.insert(0, RAG_TEMPLATES_PATH)

from src.adapters.fhir_document_adapter import FHIRDocumentAdapter

# Try multiple embedding approaches
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    import torch.nn.functional as F
    TRANSFORMERS_AVAILABLE = True
except:
    TRANSFORMERS_AVAILABLE = False


class FHIRGraphRAGQuery:
    """
    Multi-modal medical search combining vector, text, and graph methods.

    Uses RRF (Reciprocal Rank Fusion) to combine results from:
    - Vector similarity search (semantic understanding)
    - Text keyword search (exact term matching)
    - Graph traversal (entity relationships)
    """

    def __init__(self, config_path: str = "config/fhir_graphrag_config.yaml"):
        """
        Initialize query interface.

        Args:
            config_path: Path to BYOT configuration file
        """
        self.config_path = config_path
        self.config = None
        self.connection = None
        self.cursor = None
        self.adapter = None
        self.embedding_model = None

        # RRF parameters
        self.rrf_k = 60  # Standard RRF constant

    def load_config(self):
        """Load configuration from YAML file."""
        print(f"[INFO] Loading configuration from {self.config_path}...")

        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        print("[INFO] ✅ Configuration loaded")

    def connect_database(self):
        """Connect to IRIS database."""
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

    def initialize_components(self, load_embedding_model: bool = True):
        """Initialize search components."""
        print("[INFO] Initializing search components...")

        # Initialize FHIR adapter
        self.adapter = FHIRDocumentAdapter(self.connection)

        # Initialize embedding model (optional - may fail in some environments)
        self.embedding_model = None
        if load_embedding_model:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                try:
                    pipeline_config = self.config.get('pipelines', {}).get('graphrag', {})
                    embedding_model_name = pipeline_config.get('embedding_model', 'all-MiniLM-L6-v2')

                    print(f"[INFO] Loading embedding model: {embedding_model_name}...")
                    self.embedding_model = SentenceTransformer(embedding_model_name)
                    print("[INFO] ✅ Embedding model loaded")
                except Exception as e:
                    print(f"[WARN] Failed to load sentence-transformers: {e}")
                    print("[WARN] Vector search using pre-computed vectors only (no query encoding)")
                    self.embedding_model = None
            else:
                print("[WARN] sentence-transformers not available")
                print("[WARN] Vector search using keyword matching with existing vectors")
                self.embedding_model = None
        else:
            print("[INFO] Skipping embedding model (--no-vector mode)")

        print("[INFO] ✅ Components initialized")

    def vector_search(self, query: str, top_k: int = 30, patient_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            query: Search query text
            top_k: Number of results to return
            patient_id: Optional patient ID filter

        Returns:
            List of results with scores and metadata
        """
        # Skip if embedding model not available
        if self.embedding_model is None:
            print(f"[INFO] Vector search: SKIPPED (no embedding model)")
            return []

        print(f"[INFO] Vector search: top_k={top_k}, patient={patient_id or 'all'}")

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, normalize_embeddings=True, show_progress_bar=False)

        # Convert to list string format for IRIS TO_VECTOR
        vector_list_str = str(query_embedding.tolist())

        # Build query (use parameterized vector)
        if patient_id:
            sql = f"""
                SELECT TOP {top_k}
                    v.ResourceID,
                    r.ResourceString,
                    VECTOR_COSINE(v.Vector, TO_VECTOR(?, double)) as Similarity
                FROM VectorSearch.FHIRResourceVectors v
                JOIN HSFHIR_X0001_R.Rsrc r ON v.ResourceID = r.ID
                WHERE r.ResourceType = 'DocumentReference'
                AND r.Compartments LIKE ?
                AND (r.Deleted = 0 OR r.Deleted IS NULL)
                ORDER BY Similarity DESC
            """
            self.cursor.execute(sql, [vector_list_str, f'%Patient/{patient_id}%'])
        else:
            sql = f"""
                SELECT TOP {top_k}
                    v.ResourceID,
                    r.ResourceString,
                    VECTOR_COSINE(v.Vector, TO_VECTOR(?, double)) as Similarity
                FROM VectorSearch.FHIRResourceVectors v
                JOIN HSFHIR_X0001_R.Rsrc r ON v.ResourceID = r.ID
                WHERE r.ResourceType = 'DocumentReference'
                AND (r.Deleted = 0 OR r.Deleted IS NULL)
                ORDER BY Similarity DESC
            """
            self.cursor.execute(sql, [vector_list_str])

        results = []
        for row in self.cursor.fetchall():
            resource_id, resource_string, similarity = row
            results.append({
                'resource_id': resource_id,
                'score': float(similarity),
                'source': 'vector',
                'resource_string': resource_string
            })

        print(f"[INFO]   Found {len(results)} vector results")
        return results

    def text_search(self, query: str, top_k: int = 30, patient_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform text keyword search on decoded clinical notes.

        Note: Decodes hex-encoded clinical notes from FHIR DocumentReference.
        This is slower than indexed search but works without additional tables.

        Args:
            query: Search query text
            top_k: Number of results to return
            patient_id: Optional patient ID filter

        Returns:
            List of results with scores and metadata
        """
        print(f"[INFO] Text search: top_k={top_k}, patient={patient_id or 'all'}")

        # Extract keywords from query
        keywords = query.lower().split()

        # Get all DocumentReference resources (we'll decode and filter in Python)
        # Note: For production, consider creating a decoded text table with SQL Search index
        if patient_id:
            sql = """
                SELECT r.ID as ResourceID, r.ResourceString
                FROM HSFHIR_X0001_R.Rsrc r
                WHERE r.ResourceType = 'DocumentReference'
                AND r.Compartments LIKE ?
                AND (r.Deleted = 0 OR r.Deleted IS NULL)
            """
            self.cursor.execute(sql, [f'%Patient/{patient_id}%'])
        else:
            sql = """
                SELECT r.ID as ResourceID, r.ResourceString
                FROM HSFHIR_X0001_R.Rsrc r
                WHERE r.ResourceType = 'DocumentReference'
                AND (r.Deleted = 0 OR r.Deleted IS NULL)
            """
            self.cursor.execute(sql)

        import json
        results = []

        for row in self.cursor.fetchall():
            resource_id, resource_string = row

            try:
                # Parse FHIR JSON and extract clinical note
                fhir_json = json.loads(resource_string)
                clinical_note = self.adapter.extract_clinical_note(fhir_json)

                if not clinical_note:
                    continue

                # Search decoded clinical note for keywords
                clinical_note_lower = clinical_note.lower()
                score = sum(clinical_note_lower.count(kw) for kw in keywords)

                # Only include if at least one keyword matches
                if score > 0:
                    results.append({
                        'resource_id': resource_id,
                        'score': float(score),
                        'source': 'text',
                        'resource_string': resource_string
                    })

            except Exception as e:
                # Skip documents that can't be parsed
                continue

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        # Return top-k
        results = results[:top_k]

        print(f"[INFO]   Found {len(results)} text results")
        return results

    def graph_search(self, query: str, top_k: int = 10, patient_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform graph traversal search via entities.

        Args:
            query: Search query text
            top_k: Number of results to return
            patient_id: Optional patient ID filter

        Returns:
            List of results with scores and metadata
        """
        print(f"[INFO] Graph search: top_k={top_k}, patient={patient_id or 'all'}")

        # Extract keywords from query
        keywords = query.lower().split()

        # Find entities matching keywords
        entity_clauses = []
        for keyword in keywords:
            entity_clauses.append(f"LOWER(EntityText) LIKE '%{keyword}%'")

        entity_filter = " OR ".join(entity_clauses)

        # Query for matching entities and their related documents
        sql = f"""
            SELECT DISTINCT
                e.ResourceID,
                COUNT(*) as EntityMatches,
                r.ResourceString
            FROM RAG.Entities e
            JOIN HSFHIR_X0001_R.Rsrc r ON e.ResourceID = r.ID
            WHERE ({entity_filter})
            AND r.ResourceType = 'DocumentReference'
            AND (r.Deleted = 0 OR r.Deleted IS NULL)
        """

        if patient_id:
            sql += f" AND r.Compartments LIKE '%Patient/{patient_id}%'"

        sql += """
            GROUP BY e.ResourceID, r.ResourceString
            ORDER BY EntityMatches DESC
        """

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

        print(f"[INFO]   Found {len(results)} graph results")
        return results

    def rrf_fusion(self, vector_results: List[Dict], text_results: List[Dict],
                   graph_results: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).

        RRF formula: score = sum(1 / (k + rank)) for each result list

        Args:
            vector_results: Results from vector search
            text_results: Results from text search
            graph_results: Results from graph search
            top_k: Number of final results to return

        Returns:
            Fused and ranked results
        """
        print(f"[INFO] Applying RRF fusion (k={self.rrf_k})...")

        # Map resource_id to RRF score
        rrf_scores = {}
        resource_data = {}

        # Process vector results
        for rank, result in enumerate(vector_results, start=1):
            resource_id = result['resource_id']
            score = 1.0 / (self.rrf_k + rank)

            if resource_id not in rrf_scores:
                rrf_scores[resource_id] = {'vector': 0.0, 'text': 0.0, 'graph': 0.0, 'total': 0.0}
                resource_data[resource_id] = result['resource_string']

            rrf_scores[resource_id]['vector'] = score
            rrf_scores[resource_id]['total'] += score

        # Process text results
        for rank, result in enumerate(text_results, start=1):
            resource_id = result['resource_id']
            score = 1.0 / (self.rrf_k + rank)

            if resource_id not in rrf_scores:
                rrf_scores[resource_id] = {'vector': 0.0, 'text': 0.0, 'graph': 0.0, 'total': 0.0}
                resource_data[resource_id] = result['resource_string']

            rrf_scores[resource_id]['text'] = score
            rrf_scores[resource_id]['total'] += score

        # Process graph results
        for rank, result in enumerate(graph_results, start=1):
            resource_id = result['resource_id']
            score = 1.0 / (self.rrf_k + rank)

            if resource_id not in rrf_scores:
                rrf_scores[resource_id] = {'vector': 0.0, 'text': 0.0, 'graph': 0.0, 'total': 0.0}
                resource_data[resource_id] = result['resource_string']

            rrf_scores[resource_id]['graph'] = score
            rrf_scores[resource_id]['total'] += score

        # Sort by total RRF score
        fused_results = []
        for resource_id, scores in sorted(rrf_scores.items(), key=lambda x: x[1]['total'], reverse=True)[:top_k]:
            fused_results.append({
                'resource_id': resource_id,
                'rrf_score': scores['total'],
                'vector_score': scores['vector'],
                'text_score': scores['text'],
                'graph_score': scores['graph'],
                'resource_string': resource_data[resource_id]
            })

        print(f"[INFO]   Fused to {len(fused_results)} final results")
        return fused_results

    def get_document_entities(self, resource_id: int) -> List[Dict[str, Any]]:
        """Get entities extracted for a specific document."""
        sql = """
            SELECT EntityID, EntityText, EntityType, Confidence
            FROM RAG.Entities
            WHERE ResourceID = ?
            ORDER BY Confidence DESC
        """
        self.cursor.execute(sql, [resource_id])

        entities = []
        for row in self.cursor.fetchall():
            entity_id, text, entity_type, confidence = row
            entities.append({
                'id': entity_id,
                'text': text,
                'type': entity_type,
                'confidence': float(confidence)
            })

        return entities

    def get_document_relationships(self, resource_id: int) -> List[Dict[str, Any]]:
        """Get relationships for entities in a specific document."""
        sql = """
            SELECT DISTINCT
                e1.EntityText as SourceEntity,
                e1.EntityType as SourceType,
                r.RelationshipType,
                e2.EntityText as TargetEntity,
                e2.EntityType as TargetType,
                r.Confidence
            FROM RAG.EntityRelationships r
            JOIN RAG.Entities e1 ON r.SourceEntityID = e1.EntityID
            JOIN RAG.Entities e2 ON r.TargetEntityID = e2.EntityID
            WHERE r.ResourceID = ?
            ORDER BY r.Confidence DESC
        """
        self.cursor.execute(sql, [resource_id])

        relationships = []
        for row in self.cursor.fetchall():
            source_entity, source_type, rel_type, target_entity, target_type, confidence = row
            relationships.append({
                'source': f"{source_entity} ({source_type})",
                'relationship': rel_type,
                'target': f"{target_entity} ({target_type})",
                'confidence': float(confidence)
            })

        return relationships

    def display_results(self, query: str, results: List[Dict], execution_time: float):
        """Display search results in a readable format."""
        print("\n" + "="*80)
        print(f"FHIR GraphRAG Multi-Modal Search Results")
        print("="*80)
        print(f"Query: \"{query}\"")
        print(f"Execution time: {execution_time:.3f} seconds")
        print(f"Results: {len(results)} documents")
        print("="*80)

        for idx, result in enumerate(results, 1):
            print(f"\n[{idx}] Document ID: {result['resource_id']}")
            print(f"    RRF Score: {result['rrf_score']:.4f}")
            print(f"    Score breakdown:")
            print(f"      - Vector (semantic): {result['vector_score']:.4f}")
            print(f"      - Text (keywords):   {result['text_score']:.4f}")
            print(f"      - Graph (entities):  {result['graph_score']:.4f}")

            # Parse and extract clinical note
            import json
            try:
                fhir_json = json.loads(result['resource_string'])
                clinical_note = self.adapter.extract_clinical_note(fhir_json)

                # Show first 200 chars of clinical note
                preview = clinical_note[:200] + "..." if len(clinical_note) > 200 else clinical_note
                print(f"    Clinical note preview: {preview}")

                # Show entities
                entities = self.get_document_entities(result['resource_id'])
                if entities:
                    print(f"    Entities extracted ({len(entities)}):")
                    for entity in entities[:5]:  # Show top 5
                        print(f"      - {entity['text']} ({entity['type']}, conf={entity['confidence']:.2f})")
                    if len(entities) > 5:
                        print(f"      ... and {len(entities) - 5} more")

                # Show relationships
                relationships = self.get_document_relationships(result['resource_id'])
                if relationships:
                    print(f"    Relationships ({len(relationships)}):")
                    for rel in relationships[:3]:  # Show top 3
                        print(f"      - {rel['source']} --[{rel['relationship']}]--> {rel['target']}")
                    if len(relationships) > 3:
                        print(f"      ... and {len(relationships) - 3} more")

            except Exception as e:
                print(f"    [Error extracting details: {e}]")

        print("\n" + "="*80)

    def query(self, query_text: str, patient_id: Optional[int] = None,
              top_k: int = 5, vector_k: int = 30, text_k: int = 30, graph_k: int = 10):
        """
        Execute multi-modal GraphRAG query.

        Args:
            query_text: Natural language query
            patient_id: Optional patient ID filter
            top_k: Number of final results to return
            vector_k: Number of vector results to retrieve
            text_k: Number of text results to retrieve
            graph_k: Number of graph results to retrieve

        Returns:
            List of fused results
        """
        start_time = time.time()

        print(f"\n[INFO] ===== Multi-Modal Search: \"{query_text}\" =====")
        if patient_id:
            print(f"[INFO] Patient filter: {patient_id}")

        # Execute searches in parallel (conceptually - sequential for now)
        vector_results = self.vector_search(query_text, top_k=vector_k, patient_id=patient_id)
        text_results = self.text_search(query_text, top_k=text_k, patient_id=patient_id)
        graph_results = self.graph_search(query_text, top_k=graph_k, patient_id=patient_id)

        # Check if we have any results
        if not vector_results and not text_results and not graph_results:
            print("[WARN] No results found for query")
            return []

        # Fuse results with RRF
        fused_results = self.rrf_fusion(vector_results, text_results, graph_results, top_k=top_k)

        execution_time = time.time() - start_time

        # Display results
        self.display_results(query_text, fused_results, execution_time)

        # Log performance metrics
        print(f"\n[METRICS] Query latency: {execution_time:.3f}s, Results: {len(fused_results)}, "
              f"Sources: vector={len(vector_results)}, text={len(text_results)}, graph={len(graph_results)}")

        return fused_results

    def demo_queries(self):
        """Run predefined demo queries to showcase GraphRAG capabilities."""
        print("\n" + "="*80)
        print("FHIR GraphRAG Demo Queries")
        print("="*80)

        demo_queries = [
            {
                'name': "Respiratory Symptoms",
                'query': "respiratory symptoms breathing",
                'patient_id': None
            },
            {
                'name': "Medications for Hypertension",
                'query': "medications hypertension blood pressure",
                'patient_id': None
            },
            {
                'name': "Timeline of Symptoms",
                'query': "chest pain shortness of breath",
                'patient_id': None
            },
            {
                'name': "Condition-Symptom Relationships",
                'query': "diabetes symptoms treatment",
                'patient_id': None
            }
        ]

        for idx, demo in enumerate(demo_queries, 1):
            print(f"\n\n{'='*80}")
            print(f"Demo Query {idx}/{len(demo_queries)}: {demo['name']}")
            print(f"{'='*80}")

            self.query(demo['query'], patient_id=demo['patient_id'], top_k=3)

            if idx < len(demo_queries):
                input("\nPress Enter to continue to next demo query...")

    def cleanup(self):
        """Close database connections."""
        if self.adapter:
            self.adapter.close()
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()


def main():
    """Main entry point for GraphRAG query interface."""
    parser = argparse.ArgumentParser(description="FHIR GraphRAG Multi-Modal Search")
    parser.add_argument('query', nargs='?', help="Search query text")
    parser.add_argument('--patient', type=int, help="Filter by patient ID")
    parser.add_argument('--top-k', type=int, default=5, help="Number of final results (default: 5)")
    parser.add_argument('--vector-k', type=int, default=30, help="Number of vector results (default: 30)")
    parser.add_argument('--text-k', type=int, default=30, help="Number of text results (default: 30)")
    parser.add_argument('--graph-k', type=int, default=10, help="Number of graph results (default: 10)")
    parser.add_argument('--no-vector', action='store_true', help="Disable vector search (text + graph only)")
    parser.add_argument('--demo', action='store_true', help="Run demo queries")
    parser.add_argument('--config', default='config/fhir_graphrag_config.yaml', help="Config file path")

    args = parser.parse_args()

    # Validate arguments
    if not args.demo and not args.query:
        parser.error("Either provide a query or use --demo flag")

    query_interface = FHIRGraphRAGQuery(config_path=args.config)

    try:
        # Initialize
        query_interface.load_config()
        query_interface.connect_database()
        query_interface.initialize_components(load_embedding_model=not args.no_vector)

        # Check if knowledge graph is populated
        query_interface.cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        entity_count = query_interface.cursor.fetchone()[0]

        if entity_count == 0:
            print("\n[ERROR] Knowledge graph is empty!")
            print("[ERROR] Please run: python3 src/setup/fhir_graphrag_setup.py --mode=build")
            sys.exit(1)

        print(f"[INFO] Knowledge graph loaded: {entity_count} entities")

        # Execute query or demo
        if args.demo:
            query_interface.demo_queries()
        else:
            query_interface.query(
                args.query,
                patient_id=args.patient,
                top_k=args.top_k,
                vector_k=args.vector_k,
                text_k=args.text_k,
                graph_k=args.graph_k
            )

    except Exception as e:
        print(f"\n[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        query_interface.cleanup()


if __name__ == "__main__":
    main()
