"""
Medical Entity Extractor

Extracts medical entities (symptoms, conditions, medications, etc.) from clinical notes
using regex patterns and optional LLM-based extraction.

Entity Types:
- SYMPTOM: Patient-reported symptoms (e.g., "chest pain", "cough")
- CONDITION: Medical diagnoses (e.g., "hypertension", "diabetes")
- MEDICATION: Drugs and treatments (e.g., "aspirin", "insulin")
- PROCEDURE: Medical procedures (e.g., "surgery", "biopsy")
- BODY_PART: Anatomical references (e.g., "chest", "abdomen")
- TEMPORAL: Time references (e.g., "3 days ago", "last week")
"""

import re
from typing import List, Dict, Tuple, Optional


class MedicalEntityExtractor:
    """
    Hybrid entity extractor using regex patterns with confidence scoring.

    Supports fallback to regex-only mode when LLM is unavailable.
    """

    def __init__(self, min_confidence: float = 0.7, llm_enabled: bool = False):
        """
        Initialize the medical entity extractor.

        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            llm_enabled: Whether to use LLM-based extraction (fallback to regex if False)
        """
        self.min_confidence = min_confidence
        self.llm_enabled = llm_enabled

        # Compile regex patterns for each entity type
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for medical entity extraction."""

        # SYMPTOM patterns (T015)
        self.symptom_patterns = [
            (r'\b(chest pain|pain in (?:the )?chest)\b', 0.95),
            (r'\b(shortness of breath|difficulty breathing|dyspnea)\b', 0.95),
            (r'\b(cough(?:ing)?)\b', 0.85),
            (r'\b(fever|febrile|pyrexia)\b', 0.90),
            (r'\b(headache|cephalgia)\b', 0.90),
            (r'\b(nausea|vomiting|emesis)\b', 0.85),
            (r'\b(fatigue|tiredness|weakness)\b', 0.80),
            (r'\b(dizziness|vertigo)\b', 0.85),
            (r'\b(abdominal pain|stomach pain)\b', 0.90),
            (r'\b(back pain)\b', 0.85),
        ]

        # CONDITION patterns (T015)
        self.condition_patterns = [
            (r'\b(hypertension|high blood pressure|HTN)\b', 0.95),
            (r'\b(diabetes(?: mellitus)?|diabetic)\b', 0.95),
            (r'\b(asthma)\b', 0.95),
            (r'\b(bronchitis)\b', 0.90),
            (r'\b(pneumonia)\b', 0.90),
            (r'\b(coronary artery disease|CAD)\b', 0.95),
            (r'\b(congestive heart failure|CHF)\b', 0.95),
            (r'\b(chronic obstructive pulmonary disease|COPD)\b', 0.95),
            (r'\b(infection)\b', 0.75),
            (r'\b(anemia)\b', 0.90),
        ]

        # MEDICATION patterns (T015)
        self.medication_patterns = [
            (r'\b(aspirin)\b', 0.92),
            (r'\b(ibuprofen|advil|motrin)\b', 0.92),
            (r'\b(acetaminophen|tylenol|paracetamol)\b', 0.92),
            (r'\b(lisinopril)\b', 0.95),
            (r'\b(metformin)\b', 0.95),
            (r'\b(albuterol)\b', 0.95),
            (r'\b(insulin)\b', 0.92),
            (r'\b(antibiotics?)\b', 0.85),
            (r'\b(prednisone)\b', 0.92),
            (r'\b(inhaler)\b', 0.85),
        ]

        # PROCEDURE patterns (T016)
        self.procedure_patterns = [
            (r'\b(surgery|surgical procedure)\b', 0.90),
            (r'\b(biopsy)\b', 0.92),
            (r'\b(CT scan|computed tomography)\b', 0.92),
            (r'\b(MRI|magnetic resonance imaging)\b', 0.92),
            (r'\b(X-ray|radiograph)\b', 0.90),
            (r'\b(blood test|lab work)\b', 0.85),
            (r'\b(EKG|ECG|electrocardiogram)\b', 0.92),
            (r'\b(endoscopy)\b', 0.92),
            (r'\b(colonoscopy)\b', 0.92),
            (r'\b(ultrasound)\b', 0.90),
        ]

        # BODY_PART patterns (T016)
        self.body_part_patterns = [
            (r'\b(chest)\b', 0.80),
            (r'\b(abdomen|abdominal area)\b', 0.85),
            (r'\b(head)\b', 0.75),
            (r'\b(back)\b', 0.75),
            (r'\b(heart)\b', 0.85),
            (r'\b(lungs?)\b', 0.85),
            (r'\b(liver)\b', 0.90),
            (r'\b(kidney|renal)\b', 0.90),
            (r'\b(stomach)\b', 0.80),
            (r'\b(brain)\b', 0.85),
        ]

        # TEMPORAL patterns (T016)
        self.temporal_patterns = [
            (r'\b(\d+ days? ago)\b', 0.90),
            (r'\b(\d+ weeks? ago)\b', 0.90),
            (r'\b(\d+ months? ago)\b', 0.90),
            (r'\b(last week|last month|last year)\b', 0.85),
            (r'\b(yesterday|today|tomorrow)\b', 0.85),
            (r'\b((?:19|20)\d{2}-\d{2}-\d{2})\b', 0.95),  # Date format YYYY-MM-DD
            (r'\b(recently|currently|ongoing)\b', 0.75),
            (r'\b(since \d{4})\b', 0.85),
            (r'\b(for (?:the )?(?:past|last) \d+ (?:days?|weeks?|months?|years?))\b', 0.90),
        ]

        # Map entity types to pattern lists
        self.entity_type_patterns = {
            'SYMPTOM': self.symptom_patterns,
            'CONDITION': self.condition_patterns,
            'MEDICATION': self.medication_patterns,
            'PROCEDURE': self.procedure_patterns,
            'BODY_PART': self.body_part_patterns,
            'TEMPORAL': self.temporal_patterns,
        }

    def extract_entities_regex(self, text: str) -> List[Dict[str, any]]:
        """
        Extract entities using regex patterns with confidence scoring.

        Args:
            text: Clinical note text

        Returns:
            List of entities with text, type, and confidence score

        Example:
            [
                {"text": "chest pain", "type": "SYMPTOM", "confidence": 0.95},
                {"text": "aspirin", "type": "MEDICATION", "confidence": 0.92}
            ]
        """
        entities = []

        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()

        # Apply regex patterns for each entity type
        for entity_type, patterns in self.entity_type_patterns.items():
            for pattern, base_confidence in patterns:
                # Find all matches
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)

                for match in matches:
                    entity_text = match.group(1) if match.groups() else match.group(0)

                    # Adjust confidence based on context (simple heuristic)
                    confidence = base_confidence

                    # Boost confidence if entity appears in a medical context
                    if self._in_medical_context(text_lower, match.start(), match.end()):
                        confidence = min(1.0, confidence + 0.05)

                    # Only include entities above confidence threshold
                    if confidence >= self.min_confidence:
                        entities.append({
                            'text': entity_text.strip(),
                            'type': entity_type,
                            'confidence': confidence,
                            'method': 'regex'
                        })

        return entities

    def _in_medical_context(self, text: str, start_pos: int, end_pos: int, window: int = 50) -> bool:
        """
        Check if entity appears in medical context (simple heuristic).

        Args:
            text: Full text
            start_pos: Entity start position
            end_pos: Entity end position
            window: Context window size in characters

        Returns:
            True if medical context indicators found nearby
        """
        # Get context window around entity
        context_start = max(0, start_pos - window)
        context_end = min(len(text), end_pos + window)
        context = text[context_start:context_end]

        # Medical context indicators
        medical_keywords = [
            'patient', 'diagnosis', 'treatment', 'prescribed', 'reported',
            'history', 'symptom', 'condition', 'medication', 'procedure'
        ]

        # Check if any medical keywords appear in context
        return any(keyword in context for keyword in medical_keywords)

    def _deduplicate_entities(self, entities: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Remove duplicate entities, keeping highest confidence for each (text, type) pair.

        Args:
            entities: List of extracted entities

        Returns:
            Deduplicated list of entities
        """
        # Group by (text, type) and keep highest confidence
        entity_map = {}

        for entity in entities:
            key = (entity['text'].lower(), entity['type'])

            if key not in entity_map or entity['confidence'] > entity_map[key]['confidence']:
                entity_map[key] = entity

        return list(entity_map.values())

    def extract_entities(self, text: str) -> List[Dict[str, any]]:
        """
        Extract medical entities from clinical note text.

        This is the main entry point. Uses regex-only or hybrid (regex + LLM) mode
        depending on configuration.

        Args:
            text: Clinical note text

        Returns:
            Deduplicated list of entities with confidence scores
        """
        # Extract using regex
        entities = self.extract_entities_regex(text)

        # TODO: Add LLM-based extraction if enabled (future enhancement)
        if self.llm_enabled:
            # llm_entities = self.extract_entities_llm(text)
            # entities.extend(llm_entities)
            pass

        # Deduplicate
        entities = self._deduplicate_entities(entities)

        # Sort by confidence (highest first)
        entities.sort(key=lambda e: e['confidence'], reverse=True)

        return entities


# Example usage
if __name__ == "__main__":
    # Sample clinical note
    clinical_note = """
    Patient reports chest pain and shortness of breath for the past 3 days.
    History of hypertension. Prescribed aspirin for chest pain.
    Blood pressure elevated. Recommended follow-up in 2 weeks.
    """

    # Create extractor
    extractor = MedicalEntityExtractor(min_confidence=0.7)

    # Extract entities
    entities = extractor.extract_entities(clinical_note)

    # Display results
    print(f"Extracted {len(entities)} entities:\n")
    for entity in entities:
        print(f"  {entity['type']:12} | {entity['text']:30} | confidence: {entity['confidence']:.2f}")
