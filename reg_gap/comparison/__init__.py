"""Comparison module for semantic analysis and jurisdictional comparison."""

from .semantic_diff import SemanticDiff, ClauseDifference, DifferenceType
from .jurisdictional import JurisdictionalComparator, JurisdictionalGap
from .ambiguity import AmbiguityDetector, AmbiguityReport

__all__ = [
    "SemanticDiff",
    "ClauseDifference",
    "DifferenceType",
    "JurisdictionalComparator",
    "JurisdictionalGap",
    "AmbiguityDetector",
    "AmbiguityReport",
]
