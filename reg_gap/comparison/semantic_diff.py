"""
Semantic comparison of regulatory clauses using embeddings.

Compares clauses across documents and versions to identify:
- Stricter requirements
- Looser requirements  
- Ambiguous differences
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from ..parsing.clause_extractor import RegulatoryClause, ClauseType


class DifferenceType(Enum):
    """Classification of regulatory differences."""
    STRICTER = "stricter"
    LOOSER = "looser"
    AMBIGUOUS = "ambiguous"
    EQUIVALENT = "equivalent"
    CONFLICTING = "conflicting"
    NOVEL = "novel"  # No equivalent in comparison


@dataclass
class ClauseDifference:
    """Represents a difference between two clauses."""
    
    clause_a: RegulatoryClause
    clause_b: Optional[RegulatoryClause]
    difference_type: DifferenceType
    similarity_score: float
    analysis: str
    confidence: float = 0.5
    risk_factors: list[str] = field(default_factory=list)
    requires_legal_review: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'clause_a': self.clause_a.to_dict(),
            'clause_b': self.clause_b.to_dict() if self.clause_b else None,
            'difference_type': self.difference_type.value,
            'similarity_score': self.similarity_score,
            'analysis': self.analysis,
            'confidence': self.confidence,
            'risk_factors': self.risk_factors,
            'requires_legal_review': self.requires_legal_review
        }


class SemanticDiff:
    """
    Semantic comparison of regulatory clauses.
    
    Uses sentence embeddings to find similar clauses and
    classify differences between them.
    """
    
    # Keywords indicating stricter requirements
    STRICTER_INDICATORS = {
        'must', 'shall', 'required', 'mandatory', 'always', 'never',
        'prohibited', 'forbidden', 'all', 'each', 'every', 'immediately',
        'within 24 hours', 'no exceptions', 'under no circumstances'
    }
    
    # Keywords indicating looser requirements
    LOOSER_INDICATORS = {
        'may', 'can', 'optional', 'reasonable', 'generally', 'typically',
        'usually', 'unless', 'except', 'subject to', 'at discretion',
        'good faith', 'best efforts', 'commercially reasonable'
    }
    
    # Ambiguity indicators
    AMBIGUITY_INDICATORS = {
        'appropriate', 'adequate', 'sufficient', 'reasonable', 'material',
        'significant', 'substantial', 'promptly', 'timely', 'as needed',
        'as applicable', 'where appropriate', 'to the extent'
    }
    
    def __init__(
        self,
        embedding_model: Optional[Callable[[str], np.ndarray]] = None,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize SemanticDiff.
        
        Args:
            embedding_model: Optional function to generate embeddings.
                            If None, uses simple keyword-based comparison.
            similarity_threshold: Minimum similarity to consider clauses related
        """
        self.embedding_model = embedding_model
        self.similarity_threshold = similarity_threshold
        self._embeddings_cache: dict[str, np.ndarray] = {}
    
    def compare_clauses(
        self,
        clauses_a: list[RegulatoryClause],
        clauses_b: list[RegulatoryClause],
        jurisdiction_a: str = "Source",
        jurisdiction_b: str = "Target"
    ) -> list[ClauseDifference]:
        """
        Compare two sets of regulatory clauses.
        
        Args:
            clauses_a: Clauses from first document/jurisdiction
            clauses_b: Clauses from second document/jurisdiction
            jurisdiction_a: Label for first set
            jurisdiction_b: Label for second set
            
        Returns:
            List of ClauseDifference objects
        """
        differences = []
        matched_b = set()
        
        for clause_a in clauses_a:
            best_match = None
            best_similarity = 0.0
            
            for i, clause_b in enumerate(clauses_b):
                if i in matched_b:
                    continue
                
                similarity = self._calculate_similarity(clause_a.text, clause_b.text)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_match = clause_b
                    best_similarity = similarity
                    best_match_idx = i
            
            if best_match:
                matched_b.add(best_match_idx)
                diff = self._analyze_difference(clause_a, best_match, best_similarity)
            else:
                diff = ClauseDifference(
                    clause_a=clause_a,
                    clause_b=None,
                    difference_type=DifferenceType.NOVEL,
                    similarity_score=0.0,
                    analysis=f"Clause in {jurisdiction_a} has no equivalent in {jurisdiction_b}",
                    confidence=0.8,
                    requires_legal_review=True
                )
            
            differences.append(diff)
        
        # Find clauses in B with no match in A
        for i, clause_b in enumerate(clauses_b):
            if i not in matched_b:
                diff = ClauseDifference(
                    clause_a=clause_b,  # Note: using clause_a field for consistency
                    clause_b=None,
                    difference_type=DifferenceType.NOVEL,
                    similarity_score=0.0,
                    analysis=f"Clause in {jurisdiction_b} has no equivalent in {jurisdiction_a}",
                    confidence=0.8,
                    requires_legal_review=True
                )
                differences.append(diff)
        
        return differences
    
    def _calculate_similarity(self, text_a: str, text_b: str) -> float:
        """Calculate semantic similarity between two texts."""
        if self.embedding_model:
            return self._embedding_similarity(text_a, text_b)
        else:
            return self._keyword_similarity(text_a, text_b)
    
    def _embedding_similarity(self, text_a: str, text_b: str) -> float:
        """Calculate similarity using embeddings."""
        emb_a = self._get_embedding(text_a)
        emb_b = self._get_embedding(text_b)
        
        # Cosine similarity
        dot_product = np.dot(emb_a, emb_b)
        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get or compute embedding for text."""
        if text not in self._embeddings_cache:
            self._embeddings_cache[text] = self.embedding_model(text)
        return self._embeddings_cache[text]
    
    def _keyword_similarity(self, text_a: str, text_b: str) -> float:
        """Simple keyword-based similarity when embeddings unavailable."""
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        # Jaccard similarity
        return len(intersection) / len(union)
    
    def _analyze_difference(
        self,
        clause_a: RegulatoryClause,
        clause_b: RegulatoryClause,
        similarity: float
    ) -> ClauseDifference:
        """Analyze the difference between two similar clauses."""
        text_a = clause_a.text.lower()
        text_b = clause_b.text.lower()
        
        # Count indicators
        stricter_a = sum(1 for ind in self.STRICTER_INDICATORS if ind in text_a)
        stricter_b = sum(1 for ind in self.STRICTER_INDICATORS if ind in text_b)
        looser_a = sum(1 for ind in self.LOOSER_INDICATORS if ind in text_a)
        looser_b = sum(1 for ind in self.LOOSER_INDICATORS if ind in text_b)
        ambiguous_a = sum(1 for ind in self.AMBIGUITY_INDICATORS if ind in text_a)
        ambiguous_b = sum(1 for ind in self.AMBIGUITY_INDICATORS if ind in text_b)
        
        # Determine difference type
        risk_factors = []
        
        if similarity > 0.95:
            diff_type = DifferenceType.EQUIVALENT
            analysis = "Clauses are semantically equivalent"
            confidence = 0.9
        elif stricter_a > stricter_b + 1 or looser_b > looser_a + 1:
            diff_type = DifferenceType.STRICTER
            analysis = "First clause appears stricter than second"
            confidence = 0.7
            risk_factors.append("stricter_language_detected")
        elif stricter_b > stricter_a + 1 or looser_a > looser_b + 1:
            diff_type = DifferenceType.LOOSER
            analysis = "First clause appears looser than second"
            confidence = 0.7
            risk_factors.append("looser_language_detected")
        elif ambiguous_a > 2 or ambiguous_b > 2:
            diff_type = DifferenceType.AMBIGUOUS
            analysis = "Significant ambiguity in clause language"
            confidence = 0.5
            risk_factors.append("ambiguous_language")
        elif clause_a.clause_type != clause_b.clause_type:
            diff_type = DifferenceType.CONFLICTING
            analysis = f"Clause type mismatch: {clause_a.clause_type.value} vs {clause_b.clause_type.value}"
            confidence = 0.8
            risk_factors.append("clause_type_conflict")
        else:
            diff_type = DifferenceType.AMBIGUOUS
            analysis = "Difference is unclear - requires human review"
            confidence = 0.4
            risk_factors.append("unclear_difference")
        
        requires_review = (
            diff_type in (DifferenceType.AMBIGUOUS, DifferenceType.CONFLICTING) or
            confidence < 0.6 or
            len(risk_factors) > 0
        )
        
        return ClauseDifference(
            clause_a=clause_a,
            clause_b=clause_b,
            difference_type=diff_type,
            similarity_score=similarity,
            analysis=analysis,
            confidence=confidence,
            risk_factors=risk_factors,
            requires_legal_review=requires_review
        )
    
    def find_stricter_clauses(
        self,
        differences: list[ClauseDifference]
    ) -> list[ClauseDifference]:
        """Filter to only stricter clause differences."""
        return [d for d in differences if d.difference_type == DifferenceType.STRICTER]
    
    def find_looser_clauses(
        self,
        differences: list[ClauseDifference]
    ) -> list[ClauseDifference]:
        """Filter to only looser clause differences."""
        return [d for d in differences if d.difference_type == DifferenceType.LOOSER]
    
    def get_review_required(
        self,
        differences: list[ClauseDifference]
    ) -> list[ClauseDifference]:
        """Get clauses that require legal review."""
        return [d for d in differences if d.requires_legal_review]
