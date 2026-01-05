"""
Entity recognition for regulatory documents.

Identifies:
- Regulated entities (banks, brokers, advisers)
- Regulatory bodies (SEC, FINRA, FCA)
- Legal references (statutes, regulations)
- Monetary thresholds
- Time periods
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EntityType(Enum):
    """Types of regulatory entities."""
    REGULATED_ENTITY = "regulated_entity"
    REGULATORY_BODY = "regulatory_body"
    LEGAL_REFERENCE = "legal_reference"
    MONETARY_THRESHOLD = "monetary_threshold"
    TIME_PERIOD = "time_period"
    JURISDICTION = "jurisdiction"
    FINANCIAL_INSTRUMENT = "financial_instrument"
    ACTIVITY = "activity"


@dataclass
class RegulatoryEntity:
    """Represents a recognized entity in regulatory text."""
    
    text: str
    entity_type: EntityType
    normalized_form: Optional[str] = None
    start_pos: int = 0
    end_pos: int = 0
    confidence: float = 1.0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.normalized_form is None:
            self.normalized_form = self.text


class EntityRecognizer:
    """
    Recognizes regulatory entities in text.
    
    Uses pattern matching and dictionaries to identify
    regulated entities, regulatory bodies, and other
    regulatory constructs.
    """
    
    # Regulated entities
    REGULATED_ENTITIES = {
        'broker', 'dealer', 'broker-dealer', 'investment adviser',
        'investment advisor', 'registered representative', 'associated person',
        'bank', 'savings association', 'credit union', 'depository institution',
        'mutual fund', 'hedge fund', 'private fund', 'investment company',
        'issuer', 'registrant', 'reporting company', 'public company',
        'transfer agent', 'clearing agency', 'securities exchange',
        'national securities exchange', 'alternative trading system',
        'swap dealer', 'major swap participant', 'futures commission merchant',
        'commodity trading advisor', 'commodity pool operator',
        'insurance company', 'insurer', 'insurance producer',
        'money services business', 'money transmitter',
    }
    
    # Regulatory bodies
    REGULATORY_BODIES = {
        'SEC': 'Securities and Exchange Commission',
        'FINRA': 'Financial Industry Regulatory Authority',
        'CFTC': 'Commodity Futures Trading Commission',
        'FDIC': 'Federal Deposit Insurance Corporation',
        'OCC': 'Office of the Comptroller of the Currency',
        'Federal Reserve': 'Board of Governors of the Federal Reserve System',
        'CFPB': 'Consumer Financial Protection Bureau',
        'NCUA': 'National Credit Union Administration',
        'FHFA': 'Federal Housing Finance Agency',
        'FinCEN': 'Financial Crimes Enforcement Network',
        'OFAC': 'Office of Foreign Assets Control',
        'FCA': 'Financial Conduct Authority',
        'PRA': 'Prudential Regulation Authority',
        'ESMA': 'European Securities and Markets Authority',
        'EBA': 'European Banking Authority',
        'BaFin': 'Federal Financial Supervisory Authority',
        'AMF': 'Autorité des marchés financiers',
        'FSA': 'Financial Services Agency',
        'ASIC': 'Australian Securities and Investments Commission',
        'MAS': 'Monetary Authority of Singapore',
        'HKMA': 'Hong Kong Monetary Authority',
        'SFC': 'Securities and Futures Commission',
    }
    
    # Common legal references
    LEGAL_REFERENCE_PATTERNS = [
        r'(?:Section|§)\s*\d+(?:\([a-zA-Z0-9]+\))*(?:\s+of\s+(?:the\s+)?[\w\s]+Act)?',
        r'(?:Rule|Regulation)\s*\d+[a-zA-Z]*(?:-\d+)?',
        r'\d+\s*(?:U\.?S\.?C\.?|USC)\s*§?\s*\d+',
        r'\d+\s*(?:C\.?F\.?R\.?|CFR)\s*(?:Part\s*)?\d+(?:\.\d+)?',
        r'(?:Securities|Exchange|Investment Company|Investment Advisers)\s+Act\s+of\s+\d{4}',
        r'(?:Dodd-Frank|Sarbanes-Oxley|Gramm-Leach-Bliley|Bank Secrecy)\s+Act',
        r'(?:MiFID|MiFIR|GDPR|EMIR|SFDR|UCITS)\s*(?:II|III|IV|V)?',
    ]
    
    # Monetary patterns
    MONETARY_PATTERNS = [
        (r'\$\s*[\d,]+(?:\.\d{2})?\s*(?:million|billion|trillion)?', 'USD'),
        (r'(?:USD|EUR|GBP|JPY|CHF)\s*[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|trillion))?', None),
        (r'[\d,]+(?:\.\d{2})?\s*(?:dollars|euros|pounds)', None),
    ]
    
    # Time period patterns
    TIME_PATTERNS = [
        r'\d+\s*(?:business\s+)?days?',
        r'\d+\s*(?:calendar\s+)?months?',
        r'\d+\s*years?',
        r'\d+\s*(?:business\s+)?hours?',
        r'(?:annual|quarterly|monthly|daily|weekly)(?:ly)?',
        r'within\s+\d+\s+(?:days?|months?|years?)',
        r'no later than\s+\d+\s+(?:days?|months?|years?)',
    ]
    
    def __init__(self):
        # Build regex patterns
        self._regulated_entity_re = self._build_entity_pattern(self.REGULATED_ENTITIES)
        self._regulatory_body_re = self._build_body_pattern()
        self._legal_ref_re = self._compile_patterns(self.LEGAL_REFERENCE_PATTERNS)
        self._monetary_re = self._compile_monetary_patterns()
        self._time_re = self._compile_patterns(self.TIME_PATTERNS)
    
    def _build_entity_pattern(self, entities: set) -> re.Pattern:
        """Build regex pattern from entity set.

        Args:
            entities: Set of entity strings to match.

        Returns:
            Compiled regex pattern that matches any entity in the set.
        """
        # Sort by length descending to match longer phrases first
        sorted_entities = sorted(entities, key=len, reverse=True)
        pattern = '|'.join(re.escape(e) for e in sorted_entities)
        return re.compile(rf'\b({pattern})\b', re.IGNORECASE)
    
    def _build_body_pattern(self) -> re.Pattern:
        """Build pattern for regulatory bodies.

        Returns:
            Compiled regex pattern matching regulatory body abbreviations
            and full names.
        """
        abbreviations = '|'.join(re.escape(k) for k in self.REGULATORY_BODIES.keys())
        full_names = '|'.join(re.escape(v) for v in self.REGULATORY_BODIES.values())
        return re.compile(rf'\b({abbreviations}|{full_names})\b', re.IGNORECASE)
    
    def _compile_patterns(self, patterns: list[str]) -> re.Pattern:
        """Compile list of patterns into single regex.

        Args:
            patterns: List of regex pattern strings to combine.

        Returns:
            Single compiled regex pattern matching any of the input patterns.
        """
        combined = '|'.join(f'({p})' for p in patterns)
        return re.compile(combined, re.IGNORECASE)
    
    def _compile_monetary_patterns(self) -> list[tuple[re.Pattern, Optional[str]]]:
        """Compile monetary patterns with currency info.

        Returns:
            List of tuples containing compiled regex patterns and their
            associated currency codes (or None if currency is embedded
            in the pattern).
        """
        return [(re.compile(p, re.IGNORECASE), c) for p, c in self.MONETARY_PATTERNS]
    
    def recognize(self, text: str) -> list[RegulatoryEntity]:
        """
        Recognize all entities in text.
        
        Args:
            text: Regulatory text to analyze
            
        Returns:
            List of recognized RegulatoryEntity objects
        """
        entities = []
        
        # Find regulated entities
        for match in self._regulated_entity_re.finditer(text):
            entities.append(RegulatoryEntity(
                text=match.group(),
                entity_type=EntityType.REGULATED_ENTITY,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.9
            ))
        
        # Find regulatory bodies
        for match in self._regulatory_body_re.finditer(text):
            matched_text = match.group()
            normalized = self._normalize_regulatory_body(matched_text)
            entities.append(RegulatoryEntity(
                text=matched_text,
                entity_type=EntityType.REGULATORY_BODY,
                normalized_form=normalized,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.95
            ))
        
        # Find legal references
        for match in self._legal_ref_re.finditer(text):
            entities.append(RegulatoryEntity(
                text=match.group(),
                entity_type=EntityType.LEGAL_REFERENCE,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))
        
        # Find monetary thresholds
        for pattern, currency in self._monetary_re:
            for match in pattern.finditer(text):
                entities.append(RegulatoryEntity(
                    text=match.group(),
                    entity_type=EntityType.MONETARY_THRESHOLD,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                    metadata={'currency': currency} if currency else {}
                ))
        
        # Find time periods
        for match in self._time_re.finditer(text):
            entities.append(RegulatoryEntity(
                text=match.group(),
                entity_type=EntityType.TIME_PERIOD,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))
        
        # Sort by position and remove overlaps
        entities = sorted(entities, key=lambda e: (e.start_pos, -e.end_pos))
        entities = self._remove_overlaps(entities)
        
        return entities
    
    def _normalize_regulatory_body(self, text: str) -> str:
        """Normalize regulatory body name to standard form.

        Args:
            text: Regulatory body name (abbreviation or full name).

        Returns:
            Standard abbreviation for the regulatory body, or the original
            text if no match is found.
        """
        text_upper = text.upper()
        
        # Check abbreviations
        for abbrev, full in self.REGULATORY_BODIES.items():
            if text_upper == abbrev.upper():
                return abbrev
            if text.lower() == full.lower():
                return abbrev
        
        return text
    
    def _remove_overlaps(self, entities: list[RegulatoryEntity]) -> list[RegulatoryEntity]:
        """Remove overlapping entities, keeping the most specific.

        Args:
            entities: List of entities sorted by start position.

        Returns:
            List of non-overlapping entities, preferring higher confidence
            entities when overlaps occur.
        """
        if not entities:
            return []
        
        result = [entities[0]]
        
        for entity in entities[1:]:
            last = result[-1]
            
            # Check for overlap
            if entity.start_pos >= last.end_pos:
                result.append(entity)
            elif entity.confidence > last.confidence:
                result[-1] = entity
        
        return result
    
    def recognize_by_type(self, text: str, entity_type: EntityType) -> list[RegulatoryEntity]:
        """Recognize only entities of a specific type.

        Args:
            text: Regulatory text to analyze.
            entity_type: The type of entity to filter for.

        Returns:
            List of recognized RegulatoryEntity objects matching the
            specified type.
        """
        all_entities = self.recognize(text)
        return [e for e in all_entities if e.entity_type == entity_type]
    
    def get_entity_counts(self, text: str) -> dict[EntityType, int]:
        """Get count of each entity type in text.

        Args:
            text: Regulatory text to analyze.

        Returns:
            Dictionary mapping each EntityType to its count in the text.
        """
        entities = self.recognize(text)
        counts = {et: 0 for et in EntityType}
        
        for entity in entities:
            counts[entity.entity_type] += 1
        
        return counts
