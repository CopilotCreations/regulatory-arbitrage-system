"""
Confidence bounds and uncertainty quantification for risk assessments.

Provides statistical bounds on risk estimates to communicate
the inherent uncertainty in regulatory interpretation.
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class RiskInterval:
    """Represents a risk estimate with confidence bounds."""
    
    point_estimate: float  # Best estimate
    lower_bound: float     # Conservative lower bound
    upper_bound: float     # Conservative upper bound (worst case)
    confidence_level: float  # e.g., 0.95 for 95% confidence
    
    def __post_init__(self):
        """Validate that bounds are properly ordered and within valid ranges.

        Raises:
            AssertionError: If bounds are not in order (0 <= lower <= point <= upper <= 1)
                or if confidence_level is not between 0 and 1.
        """
        assert 0 <= self.lower_bound <= self.point_estimate <= self.upper_bound <= 1, \
            "Bounds must be in order: 0 <= lower <= point <= upper <= 1"
        assert 0 < self.confidence_level < 1, \
            "Confidence level must be between 0 and 1"
    
    @property
    def width(self) -> float:
        """Calculate the width of the confidence interval.

        Returns:
            The difference between upper_bound and lower_bound.
        """
        return self.upper_bound - self.lower_bound
    
    @property
    def is_wide(self) -> bool:
        """Determine whether the interval indicates high uncertainty.

        Returns:
            True if the interval width exceeds 0.3, indicating high uncertainty.
        """
        return self.width > 0.3
    
    @property
    def conservative_estimate(self) -> float:
        """Return the conservative estimate for risk planning purposes.

        Returns:
            The upper_bound value, representing the worst-case risk scenario.
        """
        return self.upper_bound
    
    def to_dict(self) -> dict:
        """Convert the RiskInterval to a dictionary for serialization.

        Returns:
            A dictionary containing point_estimate, lower_bound, upper_bound,
            confidence_level, width, and is_wide values.
        """
        return {
            'point_estimate': self.point_estimate,
            'lower_bound': self.lower_bound,
            'upper_bound': self.upper_bound,
            'confidence_level': self.confidence_level,
            'width': self.width,
            'is_wide': self.is_wide
        }


class ConfidenceBounds:
    """
    Calculates confidence bounds for risk estimates.
    
    Uses a conservative methodology that:
    1. Widens intervals for uncertain inputs
    2. Skews toward worst-case outcomes
    3. Explicitly communicates uncertainty
    """
    
    # Base uncertainty by assessment type
    BASE_UNCERTAINTY = {
        'clause_extraction': 0.15,
        'ambiguity_detection': 0.20,
        'semantic_comparison': 0.25,
        'enforcement_modeling': 0.30,
        'jurisdictional_gap': 0.20,
    }
    
    def __init__(
        self,
        confidence_level: float = 0.95,
        conservative_bias: float = 0.1
    ):
        """
        Initialize confidence bounds calculator.
        
        Args:
            confidence_level: Confidence level for intervals (e.g., 0.95)
            conservative_bias: Bias toward upper bound for planning
        """
        self.confidence_level = confidence_level
        self.conservative_bias = conservative_bias
    
    def calculate_bounds(
        self,
        point_estimate: float,
        assessment_type: str,
        sample_confidence: float = 0.5,
        n_observations: int = 1
    ) -> RiskInterval:
        """
        Calculate confidence bounds for a risk estimate.
        
        Args:
            point_estimate: Initial risk estimate (0-1)
            assessment_type: Type of assessment (affects base uncertainty)
            sample_confidence: Confidence in the input data (0-1)
            n_observations: Number of supporting observations
            
        Returns:
            RiskInterval with bounds
        """
        # Get base uncertainty for this type
        base_uncertainty = self.BASE_UNCERTAINTY.get(assessment_type, 0.25)
        
        # Adjust for sample confidence
        # Lower confidence in inputs -> wider interval
        confidence_factor = 1 + (1 - sample_confidence) * 0.5
        uncertainty = base_uncertainty * confidence_factor
        
        # Adjust for number of observations
        # More observations -> narrower interval (sqrt scaling)
        if n_observations > 1:
            uncertainty /= math.sqrt(n_observations)
        
        # Calculate z-score for confidence level
        # Approximation for normal distribution
        z = self._approximate_z_score(self.confidence_level)
        
        # Calculate interval half-width
        half_width = z * uncertainty
        
        # Apply conservative bias (shift toward higher risk)
        lower = max(0, point_estimate - half_width * (1 - self.conservative_bias))
        upper = min(1, point_estimate + half_width * (1 + self.conservative_bias))
        
        # Ensure point estimate is within bounds
        point_estimate = max(lower, min(upper, point_estimate))
        
        return RiskInterval(
            point_estimate=round(point_estimate, 4),
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            confidence_level=self.confidence_level
        )
    
    def _approximate_z_score(self, confidence: float) -> float:
        """Approximate the z-score for a given confidence level.

        Uses lookup for common values (0.90, 0.95, 0.99) and linear
        interpolation for other values.

        Args:
            confidence: The confidence level (e.g., 0.95 for 95% confidence).

        Returns:
            The approximate z-score corresponding to the confidence level.
        """
        # Common values
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }
        
        if confidence in z_scores:
            return z_scores[confidence]
        
        # Linear interpolation for other values
        if confidence < 0.90:
            return 1.645 * (confidence / 0.90)
        elif confidence < 0.95:
            return 1.645 + (1.96 - 1.645) * ((confidence - 0.90) / 0.05)
        else:
            return 1.96 + (2.576 - 1.96) * ((confidence - 0.95) / 0.04)
    
    def aggregate_intervals(
        self,
        intervals: list[RiskInterval],
        method: str = "conservative"
    ) -> RiskInterval:
        """
        Aggregate multiple risk intervals.
        
        Args:
            intervals: List of intervals to aggregate
            method: Aggregation method ("conservative", "average", "max")
            
        Returns:
            Aggregated RiskInterval
        """
        if not intervals:
            return RiskInterval(0.5, 0.25, 0.75, self.confidence_level)
        
        if method == "conservative":
            # Use highest upper bound, average point estimate
            point = sum(i.point_estimate for i in intervals) / len(intervals)
            lower = min(i.lower_bound for i in intervals)
            upper = max(i.upper_bound for i in intervals)
        
        elif method == "average":
            # Average all components
            point = sum(i.point_estimate for i in intervals) / len(intervals)
            lower = sum(i.lower_bound for i in intervals) / len(intervals)
            upper = sum(i.upper_bound for i in intervals) / len(intervals)
        
        elif method == "max":
            # Maximum of all components
            point = max(i.point_estimate for i in intervals)
            lower = max(i.lower_bound for i in intervals)
            upper = max(i.upper_bound for i in intervals)
        
        else:
            raise ValueError(f"Unknown aggregation method: {method}")
        
        # Ensure valid ordering
        point = max(lower, min(upper, point))
        
        return RiskInterval(
            point_estimate=round(point, 4),
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            confidence_level=self.confidence_level
        )
    
    def interpret_interval(self, interval: RiskInterval) -> dict:
        """
        Generate human-readable interpretation of interval.
        
        Args:
            interval: Risk interval to interpret
            
        Returns:
            Dictionary with interpretation
        """
        interpretation = {
            'summary': '',
            'uncertainty_level': '',
            'planning_guidance': '',
            'caveats': []
        }
        
        # Categorize point estimate
        if interval.point_estimate >= 0.7:
            interpretation['summary'] = "High risk"
        elif interval.point_estimate >= 0.4:
            interpretation['summary'] = "Moderate risk"
        else:
            interpretation['summary'] = "Lower risk"
        
        # Characterize uncertainty
        if interval.width >= 0.4:
            interpretation['uncertainty_level'] = "Very high uncertainty"
            interpretation['caveats'].append(
                "Wide confidence interval indicates significant uncertainty in this estimate"
            )
        elif interval.width >= 0.25:
            interpretation['uncertainty_level'] = "High uncertainty"
        elif interval.width >= 0.15:
            interpretation['uncertainty_level'] = "Moderate uncertainty"
        else:
            interpretation['uncertainty_level'] = "Lower uncertainty"
        
        # Planning guidance (always conservative)
        interpretation['planning_guidance'] = (
            f"For planning purposes, use the conservative estimate of "
            f"{interval.upper_bound:.1%} risk. This represents the upper bound of the "
            f"{interval.confidence_level:.0%} confidence interval."
        )
        
        # Standard caveats
        interpretation['caveats'].extend([
            "This is a statistical estimate, not a prediction of actual outcomes",
            "Actual regulatory outcomes depend on many factors not captured in this model",
            "Consult qualified legal counsel for compliance decisions"
        ])
        
        return interpretation
    
    def sensitivity_analysis(
        self,
        base_estimate: float,
        assessment_type: str,
        confidence_range: tuple[float, float] = (0.3, 0.9)
    ) -> list[dict]:
        """
        Perform sensitivity analysis on confidence parameter.
        
        Shows how intervals change with different input confidence levels.
        
        Args:
            base_estimate: Base risk estimate
            assessment_type: Type of assessment
            confidence_range: Range of sample confidence to test
            
        Returns:
            List of sensitivity results
        """
        results = []
        
        confidence_values = [
            confidence_range[0],
            (confidence_range[0] + confidence_range[1]) / 2,
            confidence_range[1]
        ]
        
        for conf in confidence_values:
            interval = self.calculate_bounds(
                base_estimate,
                assessment_type,
                sample_confidence=conf
            )
            
            results.append({
                'sample_confidence': conf,
                'interval': interval.to_dict(),
                'planning_estimate': interval.conservative_estimate
            })
        
        return results
