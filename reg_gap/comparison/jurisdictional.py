"""
Jurisdictional comparison of regulatory requirements.

Compares regulations across different jurisdictions to identify:
- Coverage gaps (requirements in one but not another)
- Conflict areas
- Harmonization opportunities
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..parsing.clause_extractor import RegulatoryClause, ClauseType
from ..parsing.definitions import Definition
from .semantic_diff import SemanticDiff, ClauseDifference, DifferenceType


class GapType(Enum):
    """Types of jurisdictional gaps."""
    COVERAGE_GAP = "coverage_gap"  # Requirement exists in A but not B
    STRICTER_IN_A = "stricter_in_a"
    STRICTER_IN_B = "stricter_in_b"
    DEFINITIONAL_CONFLICT = "definitional_conflict"
    THRESHOLD_DIFFERENCE = "threshold_difference"
    TIMING_DIFFERENCE = "timing_difference"
    SCOPE_DIFFERENCE = "scope_difference"
    AMBIGUITY = "ambiguity"


@dataclass
class JurisdictionalGap:
    """Represents a gap between jurisdictions."""
    
    gap_type: GapType
    jurisdiction_a: str
    jurisdiction_b: str
    description: str
    clause_a: Optional[RegulatoryClause] = None
    clause_b: Optional[RegulatoryClause] = None
    severity: float = 0.5  # 0-1 scale
    confidence: float = 0.5
    recommendations: list[str] = field(default_factory=list)
    requires_legal_review: bool = True
    
    def to_dict(self) -> dict:
        """Convert the jurisdictional gap to a dictionary for serialization.

        Returns:
            dict: A dictionary representation of the gap containing all fields
                including gap_type, jurisdictions, description, clauses,
                severity, confidence, recommendations, and review requirement.
        """
        return {
            'gap_type': self.gap_type.value,
            'jurisdiction_a': self.jurisdiction_a,
            'jurisdiction_b': self.jurisdiction_b,
            'description': self.description,
            'clause_a': self.clause_a.to_dict() if self.clause_a else None,
            'clause_b': self.clause_b.to_dict() if self.clause_b else None,
            'severity': self.severity,
            'confidence': self.confidence,
            'recommendations': self.recommendations,
            'requires_legal_review': self.requires_legal_review
        }


@dataclass
class JurisdictionProfile:
    """Profile of a jurisdiction's regulatory requirements."""
    
    jurisdiction: str
    clauses: list[RegulatoryClause]
    definitions: list[Definition]
    obligation_count: int = 0
    prohibition_count: int = 0
    permission_count: int = 0
    
    def __post_init__(self):
        self._count_clause_types()
    
    def _count_clause_types(self):
        """Count clauses by type and update instance counters.

        Updates the obligation_count, prohibition_count, and permission_count
        attributes based on the clause types present in the clauses list.
        """
        self.obligation_count = sum(1 for c in self.clauses if c.clause_type == ClauseType.OBLIGATION)
        self.prohibition_count = sum(1 for c in self.clauses if c.clause_type == ClauseType.PROHIBITION)
        self.permission_count = sum(1 for c in self.clauses if c.clause_type == ClauseType.PERMISSION)


class JurisdictionalComparator:
    """
    Compare regulatory requirements across jurisdictions.
    
    Identifies gaps, conflicts, and differences that may
    create compliance challenges for multi-jurisdictional operations.
    """
    
    def __init__(self, semantic_diff: Optional[SemanticDiff] = None):
        """
        Initialize comparator.
        
        Args:
            semantic_diff: Optional SemanticDiff instance for clause comparison
        """
        self.semantic_diff = semantic_diff or SemanticDiff()
    
    def compare(
        self,
        profile_a: JurisdictionProfile,
        profile_b: JurisdictionProfile
    ) -> list[JurisdictionalGap]:
        """
        Compare two jurisdiction profiles.
        
        Args:
            profile_a: First jurisdiction profile
            profile_b: Second jurisdiction profile
            
        Returns:
            List of identified gaps
        """
        gaps = []
        
        # Compare clauses semantically
        clause_diffs = self.semantic_diff.compare_clauses(
            profile_a.clauses,
            profile_b.clauses,
            profile_a.jurisdiction,
            profile_b.jurisdiction
        )
        
        # Convert clause differences to jurisdictional gaps
        for diff in clause_diffs:
            gap = self._diff_to_gap(diff, profile_a.jurisdiction, profile_b.jurisdiction)
            if gap:
                gaps.append(gap)
        
        # Check for definitional conflicts
        definition_gaps = self._compare_definitions(
            profile_a.definitions,
            profile_b.definitions,
            profile_a.jurisdiction,
            profile_b.jurisdiction
        )
        gaps.extend(definition_gaps)
        
        # Analyze overall regulatory burden
        burden_gaps = self._analyze_regulatory_burden(profile_a, profile_b)
        gaps.extend(burden_gaps)
        
        return gaps
    
    def _diff_to_gap(
        self,
        diff: ClauseDifference,
        jurisdiction_a: str,
        jurisdiction_b: str
    ) -> Optional[JurisdictionalGap]:
        """Convert a clause difference to a jurisdictional gap.

        Args:
            diff: The clause difference to convert.
            jurisdiction_a: Name of the first jurisdiction.
            jurisdiction_b: Name of the second jurisdiction.

        Returns:
            Optional[JurisdictionalGap]: A JurisdictionalGap if the difference
                is significant, or None if the clauses are equivalent.
        """
        
        if diff.difference_type == DifferenceType.EQUIVALENT:
            return None
        
        gap_type_map = {
            DifferenceType.STRICTER: GapType.STRICTER_IN_A,
            DifferenceType.LOOSER: GapType.STRICTER_IN_B,
            DifferenceType.AMBIGUOUS: GapType.AMBIGUITY,
            DifferenceType.CONFLICTING: GapType.SCOPE_DIFFERENCE,
            DifferenceType.NOVEL: GapType.COVERAGE_GAP,
        }
        
        gap_type = gap_type_map.get(diff.difference_type, GapType.AMBIGUITY)
        
        # Generate recommendations (NOTE: these are for review, not action)
        recommendations = self._generate_recommendations(diff, gap_type)
        
        return JurisdictionalGap(
            gap_type=gap_type,
            jurisdiction_a=jurisdiction_a,
            jurisdiction_b=jurisdiction_b,
            description=diff.analysis,
            clause_a=diff.clause_a,
            clause_b=diff.clause_b,
            severity=self._calculate_severity(diff),
            confidence=diff.confidence,
            recommendations=recommendations,
            requires_legal_review=diff.requires_legal_review
        )
    
    def _generate_recommendations(
        self,
        diff: ClauseDifference,
        gap_type: GapType
    ) -> list[str]:
        """
        Generate review recommendations (not prescriptive actions).
        
        NOTE: Recommendations emphasize legal review, not specific actions.
        """
        recommendations = []
        
        if gap_type == GapType.COVERAGE_GAP:
            recommendations.append(
                "REVIEW REQUIRED: Evaluate whether this requirement applies to your operations"
            )
        elif gap_type == GapType.STRICTER_IN_A:
            recommendations.append(
                "LEGAL REVIEW: First jurisdiction may have stricter requirements"
            )
        elif gap_type == GapType.STRICTER_IN_B:
            recommendations.append(
                "LEGAL REVIEW: Second jurisdiction may have stricter requirements"
            )
        elif gap_type == GapType.AMBIGUITY:
            recommendations.append(
                "HIGH PRIORITY REVIEW: Ambiguous language creates enforcement uncertainty"
            )
        
        if diff.requires_legal_review:
            recommendations.append(
                "MANDATORY: This gap requires qualified legal review before any decision"
            )
        
        return recommendations
    
    def _calculate_severity(self, diff: ClauseDifference) -> float:
        """Calculate severity score for a clause difference.

        Severity is based on clause type (prohibitions and obligations are more
        severe), difference type (ambiguous/conflicting increases severity),
        and confidence level (lower confidence increases severity).

        Args:
            diff: The clause difference to evaluate.

        Returns:
            float: A severity score between 0.0 and 1.0, where higher values
                indicate more severe gaps requiring greater attention.
        """
        base_severity = 0.5
        
        # Higher severity for prohibitions and obligations
        if diff.clause_a.clause_type == ClauseType.PROHIBITION:
            base_severity += 0.2
        elif diff.clause_a.clause_type == ClauseType.OBLIGATION:
            base_severity += 0.15
        
        # Higher severity for ambiguous or conflicting
        if diff.difference_type in (DifferenceType.AMBIGUOUS, DifferenceType.CONFLICTING):
            base_severity += 0.2
        
        # Lower confidence increases severity (more uncertain = more risk)
        base_severity += (1 - diff.confidence) * 0.1
        
        return min(1.0, base_severity)
    
    def _compare_definitions(
        self,
        defs_a: list[Definition],
        defs_b: list[Definition],
        jurisdiction_a: str,
        jurisdiction_b: str
    ) -> list[JurisdictionalGap]:
        """Compare definitions between jurisdictions to find conflicts.

        Identifies terms that are defined differently across jurisdictions,
        which may create compliance ambiguity or conflicts.

        Args:
            defs_a: Definitions from the first jurisdiction.
            defs_b: Definitions from the second jurisdiction.
            jurisdiction_a: Name of the first jurisdiction.
            jurisdiction_b: Name of the second jurisdiction.

        Returns:
            list[JurisdictionalGap]: A list of gaps representing definitional
                conflicts where the same term has different meanings.
        """
        gaps = []
        
        # Build lookup by term
        terms_a = {d.term.lower(): d for d in defs_a}
        terms_b = {d.term.lower(): d for d in defs_b}
        
        # Find common terms with different definitions
        common_terms = set(terms_a.keys()) & set(terms_b.keys())
        
        for term in common_terms:
            def_a = terms_a[term]
            def_b = terms_b[term]
            
            # Simple text comparison (in production, use semantic similarity)
            if def_a.definition_text.lower() != def_b.definition_text.lower():
                gap = JurisdictionalGap(
                    gap_type=GapType.DEFINITIONAL_CONFLICT,
                    jurisdiction_a=jurisdiction_a,
                    jurisdiction_b=jurisdiction_b,
                    description=f"Term '{term}' has different definitions",
                    severity=0.7,
                    confidence=0.8,
                    recommendations=[
                        f"LEGAL REVIEW: Definitional conflict for '{term}'",
                        "Determine which definition applies to your operations",
                        "Consider most restrictive interpretation for compliance"
                    ],
                    requires_legal_review=True
                )
                gaps.append(gap)
        
        return gaps
    
    def _analyze_regulatory_burden(
        self,
        profile_a: JurisdictionProfile,
        profile_b: JurisdictionProfile
    ) -> list[JurisdictionalGap]:
        """Analyze overall regulatory burden differences between jurisdictions.

        Compares the number of obligations between jurisdictions to identify
        significant scope differences that may impact compliance planning.

        Args:
            profile_a: Profile of the first jurisdiction.
            profile_b: Profile of the second jurisdiction.

        Returns:
            list[JurisdictionalGap]: A list of gaps indicating significant
                differences in regulatory burden (e.g., one jurisdiction
                having 50% more obligations than another).
        """
        gaps = []
        
        # Compare obligation counts
        if profile_a.obligation_count > profile_b.obligation_count * 1.5:
            gaps.append(JurisdictionalGap(
                gap_type=GapType.SCOPE_DIFFERENCE,
                jurisdiction_a=profile_a.jurisdiction,
                jurisdiction_b=profile_b.jurisdiction,
                description=f"{profile_a.jurisdiction} has significantly more obligations ({profile_a.obligation_count} vs {profile_b.obligation_count})",
                severity=0.6,
                confidence=0.9,
                recommendations=[
                    "Review additional obligations for applicability",
                    "Consider compliance burden in operational planning"
                ],
                requires_legal_review=True
            ))
        elif profile_b.obligation_count > profile_a.obligation_count * 1.5:
            gaps.append(JurisdictionalGap(
                gap_type=GapType.SCOPE_DIFFERENCE,
                jurisdiction_a=profile_a.jurisdiction,
                jurisdiction_b=profile_b.jurisdiction,
                description=f"{profile_b.jurisdiction} has significantly more obligations ({profile_b.obligation_count} vs {profile_a.obligation_count})",
                severity=0.6,
                confidence=0.9,
                recommendations=[
                    "Review additional obligations for applicability",
                    "Consider compliance burden in operational planning"
                ],
                requires_legal_review=True
            ))
        
        return gaps
    
    def generate_gap_matrix(
        self,
        profiles: list[JurisdictionProfile]
    ) -> dict[tuple[str, str], list[JurisdictionalGap]]:
        """
        Generate a matrix of gaps between all jurisdiction pairs.
        
        Args:
            profiles: List of jurisdiction profiles
            
        Returns:
            Dictionary mapping (jurisdiction_a, jurisdiction_b) to gaps
        """
        matrix = {}
        
        for i, profile_a in enumerate(profiles):
            for profile_b in profiles[i + 1:]:
                gaps = self.compare(profile_a, profile_b)
                matrix[(profile_a.jurisdiction, profile_b.jurisdiction)] = gaps
        
        return matrix
