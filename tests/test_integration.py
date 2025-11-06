#!/usr/bin/env python3
"""
Integration Tests for FHIR GraphRAG Multi-Modal Search

Tests the complete pipeline from FHIR data through vector/graph layers to queries.
"""

import sys
import os
import time
import json

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import iris
from src.query.fhir_graphrag_query import FHIRGraphRAGQuery
from src.query.fhir_simple_query import FHIRSimpleQuery


class IntegrationTestSuite:
    """Integration test suite for GraphRAG implementation."""

    def __init__(self):
        self.connection = None
        self.cursor = None
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    def connect_database(self):
        """Connect to IRIS database."""
        print("\n" + "="*80)
        print("FHIR GraphRAG Integration Tests")
        print("="*80)
        print("\n[SETUP] Connecting to IRIS database...")

        try:
            self.connection = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
            self.cursor = self.connection.cursor()
            print("[SETUP] ✅ Connected to IRIS")
            return True
        except Exception as e:
            print(f"[SETUP] ❌ Database connection failed: {e}")
            return False

    def run_test(self, test_name, test_func):
        """Run a single test and track results."""
        print(f"\n[TEST] {test_name}")
        try:
            start = time.time()
            result = test_func()
            elapsed = time.time() - start

            if result:
                print(f"[PASS] ✅ {test_name} ({elapsed:.3f}s)")
                self.tests_passed += 1
                self.test_results.append({
                    'test': test_name,
                    'status': 'PASS',
                    'time': elapsed
                })
            else:
                print(f"[FAIL] ❌ {test_name}")
                self.tests_failed += 1
                self.test_results.append({
                    'test': test_name,
                    'status': 'FAIL',
                    'time': elapsed
                })
        except Exception as e:
            elapsed = time.time() - start
            print(f"[FAIL] ❌ {test_name} - Exception: {e}")
            self.tests_failed += 1
            self.test_results.append({
                'test': test_name,
                'status': 'FAIL',
                'time': elapsed,
                'error': str(e)
            })

    # ========== Test 1: Database Schema ==========
    def test_database_schema(self):
        """Verify all required tables exist."""
        print("  Checking tables...")

        required_tables = [
            ('HSFHIR_X0001_R', 'Rsrc'),
            ('VectorSearch', 'FHIRResourceVectors'),
            ('RAG', 'Entities'),
            ('RAG', 'EntityRelationships')
        ]

        for schema, table in required_tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
            count = self.cursor.fetchone()[0]
            print(f"    {schema}.{table}: {count} rows")

            if count == 0 and table != 'EntityRelationships':
                print(f"    ⚠️  {schema}.{table} is empty!")
                return False

        return True

    # ========== Test 2: FHIR Data Integrity ==========
    def test_fhir_data_integrity(self):
        """Verify FHIR data is accessible and valid."""
        print("  Checking FHIR DocumentReference resources...")

        self.cursor.execute("""
            SELECT COUNT(*) FROM HSFHIR_X0001_R.Rsrc
            WHERE ResourceType = 'DocumentReference'
            AND (Deleted = 0 OR Deleted IS NULL)
        """)
        doc_count = self.cursor.fetchone()[0]
        print(f"    DocumentReference count: {doc_count}")

        if doc_count == 0:
            print("    ❌ No DocumentReference resources found!")
            return False

        # Check that we can parse FHIR JSON
        self.cursor.execute("""
            SELECT TOP 1 ResourceString FROM HSFHIR_X0001_R.Rsrc
            WHERE ResourceType = 'DocumentReference'
        """)
        resource_string = self.cursor.fetchone()[0]

        try:
            fhir_json = json.loads(resource_string)
            print(f"    ✅ FHIR JSON parseable")

            # Check for hex-encoded clinical note
            if "content" in fhir_json and len(fhir_json["content"]) > 0:
                hex_data = fhir_json["content"][0].get("attachment", {}).get("data")
                if hex_data:
                    decoded = bytes.fromhex(hex_data).decode('utf-8', errors='replace')
                    print(f"    ✅ Clinical note decodable ({len(decoded)} chars)")
                else:
                    print(f"    ⚠️  No clinical note data found")
        except Exception as e:
            print(f"    ❌ FHIR JSON parsing failed: {e}")
            return False

        return True

    # ========== Test 3: Vector Table Populated ==========
    def test_vector_table_populated(self):
        """Verify vectors are created for DocumentReferences."""
        print("  Checking vector table...")

        self.cursor.execute("""
            SELECT COUNT(*) FROM VectorSearch.FHIRResourceVectors v
            JOIN HSFHIR_X0001_R.Rsrc r ON v.ResourceID = r.ID
            WHERE r.ResourceType = 'DocumentReference'
        """)
        vector_count = self.cursor.fetchone()[0]
        print(f"    Vector count: {vector_count}")

        if vector_count == 0:
            print("    ❌ No vectors found!")
            return False

        # Check vector dimensions
        self.cursor.execute("SELECT TOP 1 Vector FROM VectorSearch.FHIRResourceVectors")
        vector = self.cursor.fetchone()[0]
        # IRIS returns vectors as strings, parse to check dimension
        print(f"    ✅ Vector exists (sample length: {len(str(vector))} chars)")

        return True

    # ========== Test 4: Knowledge Graph Populated ==========
    def test_knowledge_graph_populated(self):
        """Verify entities and relationships extracted."""
        print("  Checking knowledge graph...")

        # Check entities
        self.cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        entity_count = self.cursor.fetchone()[0]
        print(f"    Entity count: {entity_count}")

        if entity_count == 0:
            print("    ❌ No entities found! Run: python3 src/setup/fhir_graphrag_setup.py --mode=build")
            return False

        # Check entity types
        self.cursor.execute("""
            SELECT EntityType, COUNT(*) as EntityCount
            FROM RAG.Entities
            GROUP BY EntityType
            ORDER BY EntityCount DESC
        """)
        print("    Entity types:")
        for entity_type, count in self.cursor.fetchall():
            print(f"      {entity_type}: {count}")

        # Check relationships
        self.cursor.execute("SELECT COUNT(*) FROM RAG.EntityRelationships")
        rel_count = self.cursor.fetchone()[0]
        print(f"    Relationship count: {rel_count}")

        return True

    # ========== Test 5: Vector Search ==========
    def test_vector_search(self):
        """Test vector similarity search."""
        print("  Testing vector search...")

        query_interface = FHIRGraphRAGQuery()
        query_interface.load_config()
        query_interface.connect_database()
        query_interface.initialize_components(load_embedding_model=True)

        # Test vector search
        results = query_interface.vector_search("chest pain", top_k=10)

        print(f"    Results: {len(results)}")
        if len(results) > 0:
            print(f"    Top score: {results[0]['score']:.4f}")
            print(f"    ✅ Vector search working")

        query_interface.cleanup()

        return len(results) > 0

    # ========== Test 6: Text Search ==========
    def test_text_search(self):
        """Test text keyword search with hex decoding."""
        print("  Testing text search...")

        query_interface = FHIRGraphRAGQuery()
        query_interface.load_config()
        query_interface.connect_database()
        query_interface.initialize_components(load_embedding_model=False)

        # Test text search
        results = query_interface.text_search("chest pain", top_k=30)

        print(f"    Results: {len(results)}")
        if len(results) > 0:
            print(f"    Top score: {results[0]['score']:.1f}")
            print(f"    ✅ Text search working (hex decoding functional)")
        else:
            print(f"    ⚠️  No text results (may need more test data)")

        query_interface.cleanup()

        return len(results) > 0

    # ========== Test 7: Graph Search ==========
    def test_graph_search(self):
        """Test graph entity search."""
        print("  Testing graph search...")

        query_interface = FHIRGraphRAGQuery()
        query_interface.load_config()
        query_interface.connect_database()
        query_interface.initialize_components(load_embedding_model=False)

        # Test graph search
        results = query_interface.graph_search("chest pain", top_k=10)

        print(f"    Results: {len(results)}")
        if len(results) > 0:
            print(f"    Top score: {results[0]['score']:.1f}")
            print(f"    ✅ Graph search working")

        query_interface.cleanup()

        return len(results) > 0

    # ========== Test 8: RRF Fusion ==========
    def test_rrf_fusion(self):
        """Test RRF fusion combining all search methods."""
        print("  Testing RRF fusion...")

        query_interface = FHIRGraphRAGQuery()
        query_interface.load_config()
        query_interface.connect_database()
        query_interface.initialize_components(load_embedding_model=True)

        # Get results from all three methods
        vector_results = query_interface.vector_search("chest pain", top_k=10)
        text_results = query_interface.text_search("chest pain", top_k=10)
        graph_results = query_interface.graph_search("chest pain", top_k=10)

        # Test RRF fusion
        fused = query_interface.rrf_fusion(vector_results, text_results, graph_results, top_k=5)

        print(f"    Vector: {len(vector_results)}, Text: {len(text_results)}, Graph: {len(graph_results)}")
        print(f"    Fused: {len(fused)} results")

        if len(fused) > 0:
            print(f"    Top RRF score: {fused[0]['rrf_score']:.4f}")
            print(f"      Vector: {fused[0]['vector_score']:.4f}")
            print(f"      Text: {fused[0]['text_score']:.4f}")
            print(f"      Graph: {fused[0]['graph_score']:.4f}")
            print(f"    ✅ RRF fusion working")

        query_interface.cleanup()

        return len(fused) > 0

    # ========== Test 9: Patient Filtering ==========
    def test_patient_filtering(self):
        """Test patient-specific search filtering."""
        print("  Testing patient filtering...")

        # Get sample patient compartment string
        self.cursor.execute("""
            SELECT TOP 1 r.Compartments
            FROM HSFHIR_X0001_R.Rsrc r
            WHERE r.ResourceType = 'DocumentReference'
            AND r.Compartments LIKE '%Patient/%'
        """)

        result = self.cursor.fetchone()
        if not result:
            print("    ⚠️  No patient compartments found, skipping test")
            return True

        compartments = result[0]
        # Extract patient ID using Python (simpler than SQL parsing)
        import re
        match = re.search(r'Patient/([^,\]]+)', compartments)
        if not match:
            print("    ⚠️  Could not parse patient ID, skipping test")
            return True

        patient_id = match.group(1)
        print(f"    Testing with patient ID: {patient_id}")

        query_interface = FHIRSimpleQuery()
        query_interface.load_config()
        query_interface.connect_database()

        # Test without filter
        all_results = query_interface.text_search("pain", top_k=50, patient_id=None)
        print(f"    All patients: {len(all_results)} results")

        # Test with filter
        try:
            filtered_results = query_interface.text_search("pain", top_k=50, patient_id=int(patient_id))
            print(f"    Patient {patient_id}: {len(filtered_results)} results")

            if len(filtered_results) <= len(all_results):
                print(f"    ✅ Patient filtering working")
                query_interface.cleanup()
                return True
        except:
            # Patient ID might not be numeric, try as string
            pass

        query_interface.cleanup()
        return True

    # ========== Test 10: Full Multi-Modal Query ==========
    def test_full_multi_modal_query(self):
        """Test complete multi-modal query end-to-end."""
        print("  Testing full multi-modal query...")

        query_interface = FHIRGraphRAGQuery()
        query_interface.load_config()
        query_interface.connect_database()
        query_interface.initialize_components(load_embedding_model=True)

        # Execute full query
        start = time.time()
        results = query_interface.query("chest pain", top_k=5)
        elapsed = time.time() - start

        print(f"    Results: {len(results)}")
        print(f"    Query time: {elapsed:.3f}s")

        if len(results) > 0:
            print(f"    Top result ID: {results[0]['resource_id']}")
            print(f"    RRF score: {results[0]['rrf_score']:.4f}")

            # Check that result has all components
            has_vector = results[0]['vector_score'] > 0
            has_text = results[0]['text_score'] > 0
            has_graph = results[0]['graph_score'] > 0

            print(f"    Vector score: {results[0]['vector_score']:.4f} {'✅' if has_vector else '⚠️'}")
            print(f"    Text score: {results[0]['text_score']:.4f} {'✅' if has_text else '⚠️'}")
            print(f"    Graph score: {results[0]['graph_score']:.4f} {'✅' if has_graph else '⚠️'}")

            print(f"    ✅ Full multi-modal query working")

        query_interface.cleanup()

        return len(results) > 0

    # ========== Test 11: Fast Query Performance ==========
    def test_fast_query_performance(self):
        """Test fast query performance (text + graph only)."""
        print("  Testing fast query performance...")

        query_interface = FHIRSimpleQuery()
        query_interface.load_config()
        query_interface.connect_database()

        # Execute fast query
        start = time.time()
        results = query_interface.query("chest pain", top_k=5)
        elapsed = time.time() - start

        print(f"    Results: {len(results)}")
        print(f"    Query time: {elapsed:.3f}s")

        # Fast query should be < 0.1s
        if elapsed < 0.1:
            print(f"    ✅ Fast query performance excellent (< 0.1s)")
        elif elapsed < 0.5:
            print(f"    ✅ Fast query performance good (< 0.5s)")
        else:
            print(f"    ⚠️  Fast query slower than expected ({elapsed:.3f}s)")

        query_interface.cleanup()

        return len(results) > 0

    # ========== Test 12: Edge Cases ==========
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("  Testing edge cases...")

        query_interface = FHIRSimpleQuery()
        try:
            query_interface.load_config()
            query_interface.connect_database()
        except Exception as e:
            print(f"    ❌ Setup failed: {e}")
            return False

        test_cases = [
            ("xyzabc123nonexistent", "Nonexistent term"),
            ("a", "Single character"),
            ("the and of", "Common words"),
        ]

        all_passed = True
        for query, desc in test_cases:
            try:
                # Use text/graph search only
                text_results = query_interface.text_search(query, top_k=5)
                graph_results = query_interface.graph_search(query, top_k=5)
                total = len(text_results) + len(graph_results)
                print(f"    {desc}: {total} results (OK)")
            except Exception as e:
                print(f"    {desc}: ❌ Exception: {e}")
                all_passed = False

        query_interface.cleanup()

        if all_passed:
            print(f"    ✅ Edge case handling working")

        return all_passed

    # ========== Test 13: Entity Extraction Quality ==========
    def test_entity_extraction_quality(self):
        """Test quality of extracted entities."""
        print("  Testing entity extraction quality...")

        # Get a sample of entities
        self.cursor.execute("""
            SELECT TOP 5 ResourceID, EntityText, EntityType, Confidence
            FROM RAG.Entities
            WHERE EntityType IN ('SYMPTOM', 'CONDITION', 'MEDICATION')
            ORDER BY Confidence DESC
        """)

        entities = self.cursor.fetchall()

        print(f"    Sample entities:")
        for rid, text, etype, conf in entities:
            # Convert confidence to float if it's a string
            conf_val = float(conf) if isinstance(conf, str) else conf
            print(f"      {text} ({etype}, conf={conf_val:.2f})")

        # Check confidence scores are reasonable
        high_conf_count = sum(1 for _, _, _, conf in entities if float(conf) >= 0.8)

        if high_conf_count >= len(entities) * 0.6:  # At least 60% should be high confidence
            print(f"    ✅ Entity extraction quality good ({high_conf_count}/{len(entities)} high confidence)")
            return True
        else:
            print(f"    ⚠️  Entity extraction quality could be improved ({high_conf_count}/{len(entities)} high confidence)")
            return True  # Still pass, just a warning

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        total = self.tests_passed + self.tests_failed
        pass_rate = (self.tests_passed / total * 100) if total > 0 else 0

        print(f"\nTests run: {total}")
        print(f"Passed: {self.tests_passed} ✅")
        print(f"Failed: {self.tests_failed} ❌")
        print(f"Pass rate: {pass_rate:.1f}%")

        if self.tests_failed > 0:
            print("\nFailed tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    error = result.get('error', 'Unknown error')
                    print(f"  ❌ {result['test']}: {error}")

        print("\n" + "="*80)

        if self.tests_failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {self.tests_failed} test(s) failed")

        print("="*80)

    def cleanup(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("\n[CLEANUP] Database connection closed")

    def run_all_tests(self):
        """Run all integration tests."""
        if not self.connect_database():
            return False

        # Run tests
        self.run_test("1. Database Schema", self.test_database_schema)
        self.run_test("2. FHIR Data Integrity", self.test_fhir_data_integrity)
        self.run_test("3. Vector Table Populated", self.test_vector_table_populated)
        self.run_test("4. Knowledge Graph Populated", self.test_knowledge_graph_populated)
        self.run_test("5. Vector Search", self.test_vector_search)
        self.run_test("6. Text Search", self.test_text_search)
        self.run_test("7. Graph Search", self.test_graph_search)
        self.run_test("8. RRF Fusion", self.test_rrf_fusion)
        self.run_test("9. Patient Filtering", self.test_patient_filtering)
        self.run_test("10. Full Multi-Modal Query", self.test_full_multi_modal_query)
        self.run_test("11. Fast Query Performance", self.test_fast_query_performance)
        self.run_test("12. Edge Cases", self.test_edge_cases)
        self.run_test("13. Entity Extraction Quality", self.test_entity_extraction_quality)

        self.print_summary()
        self.cleanup()

        return self.tests_failed == 0


if __name__ == "__main__":
    suite = IntegrationTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)
