"""
Severity assessment for regulatory gaps and compliance risks.

Provides a consistent framework for rating the severity of
identified regulatory issues.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..parsing.clause_extractor import RegulatoryClause, ClauseType
from ..comparison.jurisdictional import JurisdictionalGap, GapType
from ..comparison.ambiguity import AmbiguityInstance


class SeverityLevel(Enum):
    """Severity levels for regulatory issues."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFORMATIONAL = 1


@dataclass
class SeverityRating:
    """A severity rating for a regulatory issue."""
    
    level: SeverityLevel
    score: float  # 0-1 scale
    factors: list[str]
    recommendation: str
    requires_immediate_attention: bool = False
    requires_legal_review: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'level': self.level.name,
            'level_value': self.level.value,
            'score': self.score,
            'factors': self.factors,
            'recommendation': self.recommendation,
            'requires_immediate_attention': self.requires_immediate_attention,
            'requires_legal_review': self.requires_legal_review
        }


class SeverityAssessor:
    """
    Assesses severity of regulatory gaps and issues.
    
    Uses a consistent methodology to rate issues on a 1-5 scale,
    enabling prioritization of compliance efforts.
    """
    
    # Gap type base severity
    GAP_TYPE_SEVERITY = {
        GapType.COVERAGE_GAP: 0.7,
        GapType.STRICTER_IN_A: 0.6,
        GapType.STRICTER_IN_B: 0.6,
        GapType.DEFINITIONAL_CONFLICT: 0.7,
        GapType.THRESHOLD_DIFFERENCE: 0.5,
        GapType.TIMING_DIFFERENCE: 0.5,
        GapType.SCOPE_DIFFERENCE: 0.6,
        GapType.AMBIGUITY: 0.65,
    }
    
    # Clause type severity multipliers
    CLAUSE_TYPE_MULTIPLIER = {
        ClauseType.PROHIBITION: 1.3,
        ClauseType.OBLIGATION: 1.2,
        ClauseType.CONDITION: 1.0,
        ClauseType.PERMISSION: 0.8,
        ClauseType.DEFINITION: 0.9,
        ClauseType.EXCEPTION: 0.9,
        ClauseType.UNKNOWN: 1.0,
    }
    
    def __init__(self, critical_threshold: float = 0.85, high_threshold: float = 0.65):
        """
        Initialize assessor.
        
        Args:
            critical_threshold: Score threshold for CRITICAL rating
            high_threshold: Score threshold for HIGH rating
        """
        self.critical_threshold = critical_threshold
        self.high_threshold = high_threshold
    
    def assess_gap(self, gap: JurisdictionalGap) -> SeverityRating:
        """
        Assess severity of a jurisdictional gap.
        
        Args:
            gap: Jurisdictional gap to assess
            
        Returns:
            SeverityRating with assessment details
        """
        factors = []
        
        # Base severity from gap type
        base_score = self.GAP_TYPE_SEVERITY.get(gap.gap_type, 0.5)
        factors.append(f"Gap type '{gap.gap_type.value}' base score: {base_score:.2f}")
        
        # Adjust for clause type if available
        if gap.clause_a:
            multiplier = self.CLAUSE_TYPE_MULTIPLIER.get(
                gap.clause_a.clause_type, 1.0
            )
            base_score *= multiplier
            factors.append(f"Clause type multiplier: {multiplier:.2f}")
        
        # Adjust for existing severity on gap
        if gap.severity > 0.5:
            base_score = (base_score + gap.severity) / 2
            factors.append(f"Combined with gap severity: {gap.severity:.2f}")
        
        # Lower confidence increases severity (uncertainty = risk)
        if gap.confidence < 0.7:
            uncertainty_penalty = (0.7 - gap.confidence) * 0.2
            base_score += uncertainty_penalty
            factors.append(f"Low confidence penalty: +{uncertainty_penalty:.2f}")
        
        # Clamp to valid range
        score = min(1.0, max(0.0, base_score))
        
        # Determine level
        level = self._score_to_level(score)
        
        # Generate recommendation
        recommendation = self._generate_gap_recommendation(gap, level)
        
        return SeverityRating(
            level=level,
            score=score,
            factors=factors,
            recommendation=recommendation,
            requires_immediate_attention=(level == SeverityLevel.CRITICAL),
            requires_legal_review=True
        )
    
    def assess_ambiguity(self, ambiguity: AmbiguityInstance) -> SeverityRating:
        """
        Assess severity of an ambiguity instance.
        
        Args:
            ambiguity: Ambiguity instance to assess
            
        Returns:
            SeverityRating with assessment details
        """
        factors = []
        
        # Base from ambiguity's own severity
        score = ambiguity.severity
        factors.append(f"Base ambiguity severity: {score:.2f}")
        
        # Confidence adjustment
        if ambiguity.confidence > 0.8:
            score *= 1.1
            factors.append("High confidence detection: +10%")
        elif ambiguity.confidence < 0.5:
            score *= 0.8
            factors.append("Low confidence detection: -20%")
        
        # Clamp
        score = min(1.0, max(0.0, score))
        
        level = self._score_to_level(score)
        
        recommendation = self._generate_ambiguity_recommendation(ambiguity, level)
        
        return SeverityRating(
            level=level,
            score=score,
            factors=factors,
            recommendation=recommendation,
            requires_immediate_attention=(level == SeverityLevel.CRITICAL),
            requires_legal_review=(level.value >= SeverityLevel.MEDIUM.value)
        )
    
    def assess_clause(self, clause: RegulatoryClause) -> SeverityRating:
        """
        Assess severity of a regulatory clause for compliance purposes.
        
        Args:
            clause: Clause to assess
            
        Returns:
            SeverityRating with assessment details
        """
        factors = []
        
        # Base from clause type
        type_scores = {
            ClauseType.PROHIBITION: 0.8,
            ClauseType.OBLIGATION: 0.7,
            ClauseType.CONDITION: 0.4,
            ClauseType.EXCEPTION: 0.3,
            ClauseType.PERMISSION: 0.2,
            ClauseType.DEFINITION: 0.2,
            ClauseType.UNKNOWN: 0.5,
        }
        
        score = type_scores.get(clause.clause_type, 0.5)
        factors.append(f"Clause type '{clause.clause_type.value}': {score:.2f}")
        
        # Adjust for clause confidence
        score *= clause.confidence
        factors.append(f"Clause confidence: {clause.confidence:.2f}")
        
        # Conditions reduce severity (more specific = more avoidable)
        if clause.conditions:
            score *= 0.9
            factors.append("Has conditions: -10%")
        
        # Exceptions reduce severity
        if clause.exceptions:
            score *= 0.85
            factors.append("Has exceptions: -15%")
        
        score = min(1.0, max(0.0, score))
        level = self._score_to_level(score)
        
        recommendation = self._generate_clause_recommendation(clause, level)
        
        return SeverityRating(
            level=level,
            score=score,
            factors=factors,
            recommendation=recommendation,
            requires_immediate_attention=(level == SeverityLevel.CRITICAL),
            requires_legal_review=(clause.clause_type in (ClauseType.PROHIBITION, ClauseType.OBLIGATION))
        )
    
    def _score_to_level(self, score: float) -> SeverityLevel:
        """Convert numeric score to severity level."""
        if score >= self.critical_threshold:
            return SeverityLevel.CRITICAL
        elif score >= self.high_threshold:
            return SeverityLevel.HIGH
        elif score >= 0.45:
            return SeverityLevel.MEDIUM
        elif score >= 0.25:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFORMATIONAL
    
    def _generate_gap_recommendation(
        self,
        gap: JurisdictionalGap,
        level: SeverityLevel
    ) -> str:
        """Generate recommendation for gap."""
        if level == SeverityLevel.CRITICAL:
            return (
                f"CRITICAL: {gap.gap_type.value} between {gap.jurisdiction_a} and "
                f"{gap.jurisdiction_b} requires immediate legal review. "
                "Do not proceed without qualified legal counsel."
            )
        elif level == SeverityLevel.HIGH:
            return (
                f"HIGH PRIORITY: Review {gap.gap_type.value} gap with legal team. "
                "Consider adopting more restrictive interpretation pending guidance."
            )
        elif level == SeverityLevel.MEDIUM:
            return (
                f"Review {gap.gap_type.value} gap as part of regular compliance review. "
                "Document your interpretation and rationale."
            )
        else:
            return "Monitor for changes. Include in periodic compliance assessment."
    
    def _generate_ambiguity_recommendation(
        self,
        ambiguity: AmbiguityInstance,
        level: SeverityLevel
    ) -> str:
        """Generate recommendation for ambiguity."""
        if level == SeverityLevel.CRITICAL:
            return (
                f"CRITICAL AMBIGUITY: '{ambiguity.trigger_phrase}' creates significant "
                "enforcement uncertainty. Seek legal guidance before proceeding."
            )
        elif level == SeverityLevel.HIGH:
            return (
                f"HIGH PRIORITY: Ambiguous term '{ambiguity.text}' should be reviewed. "
                "Consider adopting conservative interpretation."
            )
        elif level == SeverityLevel.MEDIUM:
            return (
                "Document your interpretation of ambiguous language. "
                "Include in compliance policy documentation."
            )
        else:
            return "Note ambiguity for awareness. No immediate action required."
    
    def _generate_clause_recommendation(
        self,
        clause: RegulatoryClause,
        level: SeverityLevel
    ) -> str:
        """Generate recommendation for clause."""
        if level == SeverityLevel.CRITICAL:
            return (
                f"CRITICAL: {clause.clause_type.value.upper()} requires rigorous "
                "compliance controls and legal verification."
            )
        elif level == SeverityLevel.HIGH:
            return (
                f"HIGH PRIORITY: Ensure compliance with {clause.clause_type.value}. "
                "Review with legal counsel."
            )
        elif level == SeverityLevel.MEDIUM:
            return (
                f"Include {clause.clause_type.value} in compliance procedures. "
                "Document compliance approach."
            )
        else:
            return "Standard compliance monitoring. No elevated attention required."
    
    def batch_assess(
        self,
        gaps: list[JurisdictionalGap],
        ambiguities: list[AmbiguityInstance],
        clauses: list[RegulatoryClause]
    ) -> dict:
        """
        Perform batch assessment and return summary.
        
        Args:
            gaps: Jurisdictional gaps to assess
            ambiguities: Ambiguities to assess
            clauses: Clauses to assess
            
        Returns:
            Summary dictionary with counts by severity level
        """
        ratings = []
        
        for gap in gaps:
            ratings.append(('gap', self.assess_gap(gap)))
        
        for amb in ambiguities:
            ratings.append(('ambiguity', self.assess_ambiguity(amb)))
        
        for clause in clauses:
            ratings.append(('clause', self.assess_clause(clause)))
        
        # Count by level
        counts = {level: 0 for level in SeverityLevel}
        for _, rating in ratings:
            counts[rating.level] += 1
        
        return {
            'total_assessed': len(ratings),
            'counts_by_level': {k.name: v for k, v in counts.items()},
            'critical_count': counts[SeverityLevel.CRITICAL],
            'requires_immediate_attention': sum(
                1 for _, r in ratings if r.requires_immediate_attention
            ),
            'requires_legal_review': sum(
                1 for _, r in ratings if r.requires_legal_review
            ),
            'average_score': (
                sum(r.score for _, r in ratings) / len(ratings)
                if ratings else 0
            )
        }
