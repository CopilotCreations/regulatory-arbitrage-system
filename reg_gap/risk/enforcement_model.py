"""
Conservative enforcement modeling.

Models regulatory enforcement using maximum plausible interpretation
to identify worst-case compliance scenarios.

NOTE: This model is intentionally conservative. It assumes regulators
will interpret ambiguous requirements in the most restrictive way.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..parsing.clause_extractor import RegulatoryClause, ClauseType
from ..comparison.ambiguity import AmbiguityInstance, AmbiguityType


class EnforcementLikelihood(Enum):
    """Likelihood of enforcement action."""
    VERY_LOW = 0.1
    LOW = 0.25
    MODERATE = 0.5
    HIGH = 0.75
    VERY_HIGH = 0.9


class EnforcementOutcome(Enum):
    """Possible enforcement outcomes."""
    WARNING = "warning"
    FINE = "fine"
    CEASE_AND_DESIST = "cease_and_desist"
    LICENSE_SUSPENSION = "license_suspension"
    LICENSE_REVOCATION = "license_revocation"
    CRIMINAL_REFERRAL = "criminal_referral"
    RESTITUTION = "restitution"
    INJUNCTION = "injunction"


@dataclass
class EnforcementScenario:
    """A modeled enforcement scenario."""
    
    scenario_id: str
    description: str
    interpretation: str  # How regulator might interpret
    likelihood: EnforcementLikelihood
    potential_outcomes: list[EnforcementOutcome]
    severity_score: float  # 0-1 scale
    clause: Optional[RegulatoryClause] = None
    ambiguities: list[AmbiguityInstance] = field(default_factory=list)
    mitigating_factors: list[str] = field(default_factory=list)
    aggravating_factors: list[str] = field(default_factory=list)
    requires_legal_review: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'scenario_id': self.scenario_id,
            'description': self.description,
            'interpretation': self.interpretation,
            'likelihood': self.likelihood.name,
            'potential_outcomes': [o.value for o in self.potential_outcomes],
            'severity_score': self.severity_score,
            'clause': self.clause.to_dict() if self.clause else None,
            'ambiguities': [a.to_dict() for a in self.ambiguities],
            'mitigating_factors': self.mitigating_factors,
            'aggravating_factors': self.aggravating_factors,
            'requires_legal_review': self.requires_legal_review
        }


class EnforcementModel:
    """
    Models potential enforcement scenarios conservatively.
    
    This model assumes maximum plausible interpretation by regulators
    to help identify and mitigate compliance risks.
    
    IMPORTANT: This model does not predict actual enforcement.
    It identifies theoretical maximum risk for planning purposes.
    """
    
    # Clause type to base enforcement likelihood
    CLAUSE_TYPE_LIKELIHOOD = {
        ClauseType.PROHIBITION: EnforcementLikelihood.HIGH,
        ClauseType.OBLIGATION: EnforcementLikelihood.MODERATE,
        ClauseType.CONDITION: EnforcementLikelihood.LOW,
        ClauseType.PERMISSION: EnforcementLikelihood.VERY_LOW,
        ClauseType.DEFINITION: EnforcementLikelihood.VERY_LOW,
        ClauseType.EXCEPTION: EnforcementLikelihood.LOW,
    }
    
    # Ambiguity type to enforcement impact
    AMBIGUITY_IMPACT = {
        AmbiguityType.VAGUE_STANDARD: 0.1,
        AmbiguityType.UNDEFINED_TERM: 0.15,
        AmbiguityType.SCOPE_UNCLEAR: 0.1,
        AmbiguityType.TIMING_UNCLEAR: 0.15,
        AmbiguityType.THRESHOLD_UNCLEAR: 0.2,
        AmbiguityType.CONFLICTING_CLAUSES: 0.25,
        AmbiguityType.CIRCULAR_DEFINITION: 0.1,
        AmbiguityType.REFERENCE_AMBIGUITY: 0.1,
    }
    
    def __init__(self, conservative_factor: float = 1.2):
        """
        Initialize enforcement model.
        
        Args:
            conservative_factor: Multiplier for risk estimates (>1 = more conservative)
        """
        self.conservative_factor = max(1.0, conservative_factor)
        self._scenario_counter = 0
    
    def model_clause_risk(
        self,
        clause: RegulatoryClause,
        ambiguities: Optional[list[AmbiguityInstance]] = None
    ) -> EnforcementScenario:
        """
        Model enforcement risk for a specific clause.
        
        Args:
            clause: Regulatory clause to analyze
            ambiguities: Related ambiguity instances
            
        Returns:
            EnforcementScenario with conservative risk assessment
        """
        ambiguities = ambiguities or []
        
        # Generate scenario ID
        self._scenario_counter += 1
        scenario_id = f"ENF-{self._scenario_counter:04d}"
        
        # Determine base likelihood from clause type
        base_likelihood = self.CLAUSE_TYPE_LIKELIHOOD.get(
            clause.clause_type,
            EnforcementLikelihood.MODERATE
        )
        
        # Calculate adjusted likelihood
        likelihood = self._adjust_likelihood(base_likelihood, clause, ambiguities)
        
        # Determine potential outcomes
        outcomes = self._determine_outcomes(clause, likelihood)
        
        # Calculate severity
        severity = self._calculate_severity(clause, ambiguities, outcomes)
        
        # Generate maximum interpretation
        interpretation = self._generate_max_interpretation(clause, ambiguities)
        
        # Identify factors
        mitigating = self._identify_mitigating_factors(clause)
        aggravating = self._identify_aggravating_factors(clause, ambiguities)
        
        return EnforcementScenario(
            scenario_id=scenario_id,
            description=f"Enforcement scenario for {clause.clause_type.value} clause",
            interpretation=interpretation,
            likelihood=likelihood,
            potential_outcomes=outcomes,
            severity_score=severity,
            clause=clause,
            ambiguities=ambiguities,
            mitigating_factors=mitigating,
            aggravating_factors=aggravating,
            requires_legal_review=True
        )
    
    def _adjust_likelihood(
        self,
        base: EnforcementLikelihood,
        clause: RegulatoryClause,
        ambiguities: list[AmbiguityInstance]
    ) -> EnforcementLikelihood:
        """Adjust likelihood based on clause characteristics."""
        score = base.value
        
        # Ambiguity increases risk (regulators may interpret strictly)
        for amb in ambiguities:
            impact = self.AMBIGUITY_IMPACT.get(amb.ambiguity_type, 0.1)
            score += impact * amb.severity
        
        # Apply conservative factor
        score *= self.conservative_factor
        
        # Clamp to valid range
        score = min(0.95, max(0.05, score))
        
        # Map back to enum
        if score >= 0.8:
            return EnforcementLikelihood.VERY_HIGH
        elif score >= 0.6:
            return EnforcementLikelihood.HIGH
        elif score >= 0.4:
            return EnforcementLikelihood.MODERATE
        elif score >= 0.2:
            return EnforcementLikelihood.LOW
        else:
            return EnforcementLikelihood.VERY_LOW
    
    def _determine_outcomes(
        self,
        clause: RegulatoryClause,
        likelihood: EnforcementLikelihood
    ) -> list[EnforcementOutcome]:
        """Determine potential enforcement outcomes."""
        outcomes = []
        
        # Base outcomes on clause type
        if clause.clause_type == ClauseType.PROHIBITION:
            outcomes.extend([
                EnforcementOutcome.CEASE_AND_DESIST,
                EnforcementOutcome.FINE,
            ])
            if likelihood.value >= 0.7:
                outcomes.append(EnforcementOutcome.LICENSE_SUSPENSION)
        
        elif clause.clause_type == ClauseType.OBLIGATION:
            outcomes.append(EnforcementOutcome.WARNING)
            if likelihood.value >= 0.5:
                outcomes.append(EnforcementOutcome.FINE)
            if likelihood.value >= 0.75:
                outcomes.append(EnforcementOutcome.CEASE_AND_DESIST)
        
        else:
            outcomes.append(EnforcementOutcome.WARNING)
        
        return outcomes
    
    def _calculate_severity(
        self,
        clause: RegulatoryClause,
        ambiguities: list[AmbiguityInstance],
        outcomes: list[EnforcementOutcome]
    ) -> float:
        """Calculate overall severity score."""
        # Base severity from outcomes
        outcome_severity = {
            EnforcementOutcome.WARNING: 0.1,
            EnforcementOutcome.FINE: 0.4,
            EnforcementOutcome.CEASE_AND_DESIST: 0.6,
            EnforcementOutcome.LICENSE_SUSPENSION: 0.8,
            EnforcementOutcome.LICENSE_REVOCATION: 0.95,
            EnforcementOutcome.CRIMINAL_REFERRAL: 1.0,
            EnforcementOutcome.RESTITUTION: 0.5,
            EnforcementOutcome.INJUNCTION: 0.7,
        }
        
        if outcomes:
            max_outcome_severity = max(outcome_severity.get(o, 0.5) for o in outcomes)
        else:
            max_outcome_severity = 0.3
        
        # Adjust for ambiguity count
        ambiguity_factor = min(0.3, len(ambiguities) * 0.05)
        
        # Apply conservative factor
        severity = (max_outcome_severity + ambiguity_factor) * self.conservative_factor
        
        return min(1.0, severity)
    
    def _generate_max_interpretation(
        self,
        clause: RegulatoryClause,
        ambiguities: list[AmbiguityInstance]
    ) -> str:
        """Generate maximum plausible interpretation description."""
        parts = ["MAXIMUM INTERPRETATION: "]
        
        if clause.clause_type == ClauseType.PROHIBITION:
            parts.append("This prohibition would be interpreted to cover the broadest possible scope. ")
        elif clause.clause_type == ClauseType.OBLIGATION:
            parts.append("This obligation would be interpreted with the strictest compliance standards. ")
        
        # Address ambiguities
        for amb in ambiguities[:3]:  # Top 3 ambiguities
            if amb.ambiguity_type == AmbiguityType.VAGUE_STANDARD:
                parts.append(f"'{amb.text}' would be interpreted against the regulated entity. ")
            elif amb.ambiguity_type == AmbiguityType.TIMING_UNCLEAR:
                parts.append("Timing requirements would be interpreted as requiring immediate action. ")
            elif amb.ambiguity_type == AmbiguityType.THRESHOLD_UNCLEAR:
                parts.append("Thresholds would be set at the most stringent reasonable level. ")
        
        parts.append("This represents a conservative planning scenario, not a prediction.")
        
        return "".join(parts)
    
    def _identify_mitigating_factors(self, clause: RegulatoryClause) -> list[str]:
        """Identify factors that might reduce enforcement risk."""
        factors = []
        
        if clause.conditions:
            factors.append("Clause contains explicit conditions that may limit applicability")
        
        if clause.exceptions:
            factors.append("Clause contains exceptions that may provide safe harbors")
        
        if clause.clause_type == ClauseType.PERMISSION:
            factors.append("Clause is permissive rather than mandatory")
        
        return factors
    
    def _identify_aggravating_factors(
        self,
        clause: RegulatoryClause,
        ambiguities: list[AmbiguityInstance]
    ) -> list[str]:
        """Identify factors that might increase enforcement risk."""
        factors = []
        
        if clause.clause_type == ClauseType.PROHIBITION:
            factors.append("Prohibition clauses typically face stricter enforcement")
        
        high_severity_amb = [a for a in ambiguities if a.severity >= 0.7]
        if high_severity_amb:
            factors.append(f"{len(high_severity_amb)} high-severity ambiguities increase interpretation risk")
        
        if not clause.conditions and not clause.exceptions:
            factors.append("No explicit conditions or exceptions limits flexibility")
        
        return factors
    
    def generate_scenario_report(
        self,
        scenarios: list[EnforcementScenario]
    ) -> dict:
        """
        Generate a summary report of enforcement scenarios.
        
        Args:
            scenarios: List of scenarios to summarize
            
        Returns:
            Summary report dictionary
        """
        if not scenarios:
            return {
                'total_scenarios': 0,
                'message': 'No enforcement scenarios modeled'
            }
        
        high_risk = [s for s in scenarios if s.likelihood.value >= 0.7]
        moderate_risk = [s for s in scenarios if 0.4 <= s.likelihood.value < 0.7]
        low_risk = [s for s in scenarios if s.likelihood.value < 0.4]
        
        avg_severity = sum(s.severity_score for s in scenarios) / len(scenarios)
        
        return {
            'total_scenarios': len(scenarios),
            'high_risk_count': len(high_risk),
            'moderate_risk_count': len(moderate_risk),
            'low_risk_count': len(low_risk),
            'average_severity': round(avg_severity, 3),
            'max_severity': max(s.severity_score for s in scenarios),
            'all_require_review': all(s.requires_legal_review for s in scenarios),
            'disclaimer': (
                "This analysis uses conservative modeling for planning purposes. "
                "Actual enforcement outcomes depend on many factors not captured here. "
                "Consult qualified legal counsel before making compliance decisions."
            )
        }
