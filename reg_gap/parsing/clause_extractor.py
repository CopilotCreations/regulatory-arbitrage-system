"""
Clause extraction from regulatory documents.

Identifies and classifies regulatory clauses as:
- Obligations (must, shall, required)
- Prohibitions (must not, shall not, prohibited)
- Permissions (may, permitted)
- Conditions (if, when, where, unless)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ClauseType(Enum):
    """Types of regulatory clauses."""
    OBLIGATION = "obligation"
    PROHIBITION = "prohibition"
    PERMISSION = "permission"
    CONDITION = "condition"
    DEFINITION = "definition"
    EXCEPTION = "exception"
    UNKNOWN = "unknown"


@dataclass
class RegulatoryClause:
    """Represents an extracted regulatory clause."""
    
    text: str
    clause_type: ClauseType
    section_id: Optional[str] = None
    subject: Optional[str] = None
    action: Optional[str] = None
    object_: Optional[str] = None
    conditions: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    position: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'text': self.text,
            'clause_type': self.clause_type.value,
            'section_id': self.section_id,
            'subject': self.subject,
            'action': self.action,
            'object': self.object_,
            'conditions': self.conditions,
            'exceptions': self.exceptions,
            'confidence': self.confidence,
            'position': self.position
        }


class ClauseExtractor:
    """
    Extracts and classifies regulatory clauses.
    
    Uses pattern matching and linguistic analysis to identify
    obligations, prohibitions, permissions, and conditions.
    """
    
    # Modal verb patterns for classification
    OBLIGATION_PATTERNS = [
        r'\b(?:shall|must|will|is required to|are required to|has to|have to)\b',
        r'\b(?:is obligated|are obligated|is obliged|are obliged)\b',
        r'\b(?:it is mandatory|mandatory requirement)\b',
    ]
    
    PROHIBITION_PATTERNS = [
        r'\b(?:shall not|must not|may not|cannot|will not)\b',
        r'\b(?:is prohibited|are prohibited|is forbidden|are forbidden)\b',
        r'\b(?:is not permitted|are not permitted|is not allowed|are not allowed)\b',
        r'\b(?:no person shall|no entity shall|no one may)\b',
        r'\bno\s+[\w-]+(?:\s+[\w-]+)?\s+shall\b',  # "No X shall" pattern (handles hyphens)
    ]
    
    PERMISSION_PATTERNS = [
        r'\b(?:may|can|is permitted to|are permitted to)\b',
        r'\b(?:is allowed to|are allowed to|is authorized|are authorized)\b',
        r'\b(?:has the right to|have the right to)\b',
    ]
    
    CONDITION_PATTERNS = [
        r'\b(?:if|when|where|unless|provided that|subject to)\b',
        r'\b(?:in the event|in case of|contingent upon)\b',
        r'\b(?:except when|except where|except if)\b',
    ]
    
    EXCEPTION_PATTERNS = [
        r'\b(?:except|excluding|other than|notwithstanding)\b',
        r'\b(?:this (?:section|rule|regulation) does not apply)\b',
        r'\b(?:exemption|exempt from)\b',
    ]
    
    def __init__(self, min_clause_length: int = 20, max_clause_length: int = 1000):
        self.min_clause_length = min_clause_length
        self.max_clause_length = max_clause_length
        
        # Compile patterns for efficiency
        self._obligation_re = self._compile_patterns(self.OBLIGATION_PATTERNS)
        self._prohibition_re = self._compile_patterns(self.PROHIBITION_PATTERNS)
        self._permission_re = self._compile_patterns(self.PERMISSION_PATTERNS)
        self._condition_re = self._compile_patterns(self.CONDITION_PATTERNS)
        self._exception_re = self._compile_patterns(self.EXCEPTION_PATTERNS)
    
    def _compile_patterns(self, patterns: list[str]) -> re.Pattern:
        """Compile list of patterns into single regex."""
        combined = '|'.join(f'({p})' for p in patterns)
        return re.compile(combined, re.IGNORECASE)
    
    def extract(self, text: str, section_id: Optional[str] = None) -> list[RegulatoryClause]:
        """
        Extract regulatory clauses from text.
        
        Args:
            text: Regulatory text to analyze
            section_id: Optional section identifier for context
            
        Returns:
            List of extracted RegulatoryClause objects
        """
        clauses = []
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        for i, sentence in enumerate(sentences):
            if len(sentence) < self.min_clause_length:
                continue
            if len(sentence) > self.max_clause_length:
                sentence = sentence[:self.max_clause_length] + "..."
            
            clause_type = self._classify_clause(sentence)
            
            if clause_type != ClauseType.UNKNOWN:
                clause = RegulatoryClause(
                    text=sentence,
                    clause_type=clause_type,
                    section_id=section_id,
                    confidence=self._calculate_confidence(sentence, clause_type),
                    position=i
                )
                
                # Extract structured components
                clause.subject = self._extract_subject(sentence)
                clause.action = self._extract_action(sentence)
                clause.conditions = self._extract_conditions(sentence)
                clause.exceptions = self._extract_exceptions(sentence)
                
                clauses.append(clause)
        
        return clauses
    
    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle common abbreviations to avoid false splits
        text = re.sub(r'\b(Mr|Mrs|Dr|Inc|Ltd|etc|vs|i\.e|e\.g)\.\s', r'\1<PERIOD> ', text)
        
        # Split on sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Restore periods
        sentences = [s.replace('<PERIOD>', '.') for s in sentences]
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _classify_clause(self, sentence: str) -> ClauseType:
        """Classify a sentence by its regulatory nature."""
        # Check patterns in order of specificity
        if self._prohibition_re.search(sentence):
            return ClauseType.PROHIBITION
        if self._obligation_re.search(sentence):
            return ClauseType.OBLIGATION
        if self._permission_re.search(sentence):
            return ClauseType.PERMISSION
        if self._exception_re.search(sentence):
            return ClauseType.EXCEPTION
        if self._condition_re.search(sentence):
            return ClauseType.CONDITION
        if self._is_definition(sentence):
            return ClauseType.DEFINITION
        
        return ClauseType.UNKNOWN
    
    def _is_definition(self, sentence: str) -> bool:
        """Check if sentence is a definition."""
        definition_patterns = [
            r'"[^"]+" means',
            r'"[^"]+" shall mean',
            r'(?:the term|The term) "[^"]+"',
            r'"[^"]+" is defined as',
        ]
        return any(re.search(p, sentence) for p in definition_patterns)
    
    def _calculate_confidence(self, sentence: str, clause_type: ClauseType) -> float:
        """Calculate confidence score for classification."""
        confidence = 0.5  # Base confidence
        
        # Multiple indicators increase confidence
        patterns = {
            ClauseType.OBLIGATION: self.OBLIGATION_PATTERNS,
            ClauseType.PROHIBITION: self.PROHIBITION_PATTERNS,
            ClauseType.PERMISSION: self.PERMISSION_PATTERNS,
            ClauseType.CONDITION: self.CONDITION_PATTERNS,
            ClauseType.EXCEPTION: self.EXCEPTION_PATTERNS,
        }
        
        if clause_type in patterns:
            matches = sum(1 for p in patterns[clause_type] if re.search(p, sentence, re.IGNORECASE))
            confidence += min(0.4, matches * 0.15)
        
        # Longer sentences with clear structure are more confident
        if len(sentence.split()) > 10:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _extract_subject(self, sentence: str) -> Optional[str]:
        """Extract the subject of the clause."""
        # Common regulatory subjects
        subject_patterns = [
            r'^((?:The |A |An )?(?:registrant|issuer|broker|dealer|investment adviser|'
            r'fund|person|entity|company|firm|institution|bank|covered person))',
            r'^((?:The |A |An )?(?:licensee|applicant|member|participant|customer|client))',
            r'^(No (?:person|entity|one|broker|dealer|adviser))',
        ]
        
        for pattern in subject_patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_action(self, sentence: str) -> Optional[str]:
        """Extract the main action/verb phrase."""
        # Look for modal + verb patterns
        action_pattern = r'(?:shall|must|may|will|should|can)\s+(?:not\s+)?(\w+(?:\s+\w+)?)'
        match = re.search(action_pattern, sentence, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_conditions(self, sentence: str) -> list[str]:
        """Extract conditional clauses."""
        conditions = []
        
        condition_patterns = [
            r'if\s+([^,;.]+)',
            r'when\s+([^,;.]+)',
            r'where\s+([^,;.]+)',
            r'provided that\s+([^,;.]+)',
            r'subject to\s+([^,;.]+)',
        ]
        
        for pattern in condition_patterns:
            for match in re.finditer(pattern, sentence, re.IGNORECASE):
                conditions.append(match.group(1).strip())
        
        return conditions
    
    def _extract_exceptions(self, sentence: str) -> list[str]:
        """Extract exception clauses."""
        exceptions = []
        
        exception_patterns = [
            r'except\s+(?:that\s+)?([^,;.]+)',
            r'unless\s+([^,;.]+)',
            r'excluding\s+([^,;.]+)',
            r'other than\s+([^,;.]+)',
        ]
        
        for pattern in exception_patterns:
            for match in re.finditer(pattern, sentence, re.IGNORECASE):
                exceptions.append(match.group(1).strip())
        
        return exceptions
    
    def extract_all_types(self, text: str) -> dict[ClauseType, list[RegulatoryClause]]:
        """Extract and group clauses by type."""
        clauses = self.extract(text)
        
        grouped = {ct: [] for ct in ClauseType}
        for clause in clauses:
            grouped[clause.clause_type].append(clause)
        
        return grouped
