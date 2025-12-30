"""
Definition extraction and management for regulatory documents.

Extracts defined terms and their definitions, enabling:
- Cross-referencing across documents
- Identifying definitional conflicts
- Building term glossaries
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Definition:
    """Represents an extracted definition."""
    
    term: str
    definition_text: str
    source_document: Optional[str] = None
    section_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    position: int = 0
    confidence: float = 1.0
    cross_references: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'term': self.term,
            'definition_text': self.definition_text,
            'source_document': self.source_document,
            'section_id': self.section_id,
            'jurisdiction': self.jurisdiction,
            'position': self.position,
            'confidence': self.confidence,
            'cross_references': self.cross_references
        }


class DefinitionExtractor:
    """
    Extracts and manages regulatory definitions.
    
    Identifies various definition patterns commonly used
    in regulatory texts.
    """
    
    # Definition patterns in order of specificity
    DEFINITION_PATTERNS = [
        # "term" means X
        (r'"([^"]+)"\s+means\s+(.+?)(?=\.|;|\n\n|$)', 0.95),
        # "term" shall mean X
        (r'"([^"]+)"\s+shall\s+mean\s+(.+?)(?=\.|;|\n\n|$)', 0.95),
        # "term" is defined as X
        (r'"([^"]+)"\s+is\s+defined\s+as\s+(.+?)(?=\.|;|\n\n|$)', 0.9),
        # "term" refers to X
        (r'"([^"]+)"\s+refers\s+to\s+(.+?)(?=\.|;|\n\n|$)', 0.85),
        # The term "term" means X
        (r'[Tt]he\s+term\s+"([^"]+)"\s+means\s+(.+?)(?=\.|;|\n\n|$)', 0.95),
        # For purposes of this section, "term" means X
        (r'[Ff]or\s+(?:the\s+)?purposes?\s+of\s+this\s+(?:section|rule|regulation|part),?\s+"([^"]+)"\s+means\s+(.+?)(?=\.|;|\n\n|$)', 0.9),
        # "term" has the meaning given in X
        (r'"([^"]+)"\s+has\s+the\s+(?:same\s+)?meaning\s+(?:given|set forth|provided)\s+in\s+(.+?)(?=\.|;|\n\n|$)', 0.8),
        # As used in this section, "term" means
        (r'[Aa]s\s+used\s+in\s+this\s+(?:section|rule|regulation|part),?\s+"([^"]+)"\s+means\s+(.+?)(?=\.|;|\n\n|$)', 0.9),
        # (term) - definition in parenthetical context
        (r'\(([^)]+)\)\s*[-–—]\s*(.+?)(?=\.|;|\n\n|\)|$)', 0.7),
    ]
    
    # Patterns for cross-references in definitions
    CROSS_REFERENCE_PATTERNS = [
        r'as\s+defined\s+in\s+(?:Section|§|Rule)\s*(\d+(?:\.\d+)*)',
        r'within\s+the\s+meaning\s+of\s+(?:Section|§|Rule)\s*(\d+(?:\.\d+)*)',
        r'pursuant\s+to\s+(?:Section|§|Rule)\s*(\d+(?:\.\d+)*)',
        r'see\s+(?:Section|§|Rule)\s*(\d+(?:\.\d+)*)',
    ]
    
    def __init__(self, min_definition_length: int = 10, max_definition_length: int = 2000):
        self.min_definition_length = min_definition_length
        self.max_definition_length = max_definition_length
        
        # Compile patterns
        self._patterns = [(re.compile(p, re.IGNORECASE | re.DOTALL), c) for p, c in self.DEFINITION_PATTERNS]
        self._xref_patterns = [re.compile(p, re.IGNORECASE) for p in self.CROSS_REFERENCE_PATTERNS]
    
    def extract(
        self,
        text: str,
        source_document: Optional[str] = None,
        jurisdiction: Optional[str] = None
    ) -> list[Definition]:
        """
        Extract definitions from regulatory text.
        
        Args:
            text: Regulatory text to analyze
            source_document: Optional source document identifier
            jurisdiction: Optional jurisdiction identifier
            
        Returns:
            List of extracted Definition objects
        """
        definitions = []
        seen_terms = set()
        
        for pattern, confidence in self._patterns:
            for match in pattern.finditer(text):
                term = match.group(1).strip()
                definition_text = match.group(2).strip()
                
                # Skip if already found this term
                term_lower = term.lower()
                if term_lower in seen_terms:
                    continue
                
                # Validate definition
                if not self._is_valid_definition(term, definition_text):
                    continue
                
                # Extract cross-references
                cross_refs = self._extract_cross_references(definition_text)
                
                definition = Definition(
                    term=term,
                    definition_text=definition_text,
                    source_document=source_document,
                    jurisdiction=jurisdiction,
                    position=match.start(),
                    confidence=confidence,
                    cross_references=cross_refs
                )
                
                definitions.append(definition)
                seen_terms.add(term_lower)
        
        return sorted(definitions, key=lambda d: d.position)
    
    def _is_valid_definition(self, term: str, definition_text: str) -> bool:
        """Validate that the extraction is a real definition."""
        # Term should be reasonable length
        if len(term) < 2 or len(term) > 100:
            return False
        
        # Definition should be substantial
        if len(definition_text) < self.min_definition_length:
            return False
        
        if len(definition_text) > self.max_definition_length:
            return False
        
        # Term shouldn't be mostly numbers
        if sum(c.isdigit() for c in term) > len(term) / 2:
            return False
        
        return True
    
    def _extract_cross_references(self, definition_text: str) -> list[str]:
        """Extract cross-references from definition text."""
        refs = []
        
        for pattern in self._xref_patterns:
            for match in pattern.finditer(definition_text):
                refs.append(match.group(1))
        
        return list(set(refs))
    
    def find_conflicts(self, definitions: list[Definition]) -> list[dict]:
        """
        Find conflicting definitions for the same term.
        
        Args:
            definitions: List of definitions to analyze
            
        Returns:
            List of conflict records
        """
        # Group by normalized term
        by_term: dict[str, list[Definition]] = {}
        
        for defn in definitions:
            term_lower = defn.term.lower()
            if term_lower not in by_term:
                by_term[term_lower] = []
            by_term[term_lower].append(defn)
        
        # Find terms with multiple definitions
        conflicts = []
        
        for term, defs in by_term.items():
            if len(defs) > 1:
                # Check if definitions actually differ
                unique_texts = set(d.definition_text.lower()[:200] for d in defs)
                
                if len(unique_texts) > 1:
                    conflicts.append({
                        'term': term,
                        'definitions': [d.to_dict() for d in defs],
                        'jurisdictions': list(set(d.jurisdiction for d in defs if d.jurisdiction)),
                        'conflict_type': self._classify_conflict(defs)
                    })
        
        return conflicts
    
    def _classify_conflict(self, definitions: list[Definition]) -> str:
        """Classify the type of definitional conflict."""
        # Simple heuristic based on definition length differences
        lengths = [len(d.definition_text) for d in definitions]
        max_len = max(lengths)
        min_len = min(lengths)
        
        if max_len > min_len * 2:
            return "scope_difference"
        
        jurisdictions = set(d.jurisdiction for d in definitions if d.jurisdiction)
        if len(jurisdictions) > 1:
            return "jurisdictional"
        
        return "semantic"
    
    def build_glossary(self, definitions: list[Definition]) -> dict[str, dict]:
        """
        Build a glossary from extracted definitions.
        
        For terms with multiple definitions, includes all variants.
        
        Args:
            definitions: List of definitions
            
        Returns:
            Glossary dictionary with terms and their definitions
        """
        glossary = {}
        
        for defn in definitions:
            term = defn.term
            
            if term not in glossary:
                glossary[term] = {
                    'primary_definition': defn.definition_text,
                    'variants': [],
                    'sources': [defn.source_document] if defn.source_document else [],
                    'jurisdictions': [defn.jurisdiction] if defn.jurisdiction else [],
                    'cross_references': defn.cross_references
                }
            else:
                # Add as variant if different
                existing = glossary[term]
                if defn.definition_text != existing['primary_definition']:
                    existing['variants'].append({
                        'definition': defn.definition_text,
                        'source': defn.source_document,
                        'jurisdiction': defn.jurisdiction
                    })
                
                if defn.source_document and defn.source_document not in existing['sources']:
                    existing['sources'].append(defn.source_document)
                
                if defn.jurisdiction and defn.jurisdiction not in existing['jurisdictions']:
                    existing['jurisdictions'].append(defn.jurisdiction)
                
                existing['cross_references'].extend(defn.cross_references)
                existing['cross_references'] = list(set(existing['cross_references']))
        
        return glossary
