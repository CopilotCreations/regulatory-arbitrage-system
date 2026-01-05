"""
Ambiguity detection in regulatory text.

Identifies language that could be interpreted multiple ways,
creating enforcement uncertainty and compliance risk.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AmbiguityType(Enum):
    """Types of regulatory ambiguity."""
    VAGUE_STANDARD = "vague_standard"  # e.g., "reasonable", "appropriate"
    UNDEFINED_TERM = "undefined_term"  # Terms used but not defined
    CIRCULAR_DEFINITION = "circular_definition"
    CONFLICTING_CLAUSES = "conflicting_clauses"
    SCOPE_UNCLEAR = "scope_unclear"  # Who does this apply to?
    TIMING_UNCLEAR = "timing_unclear"  # When must compliance occur?
    THRESHOLD_UNCLEAR = "threshold_unclear"  # What triggers the requirement?
    REFERENCE_AMBIGUITY = "reference_ambiguity"  # Unclear cross-references


@dataclass
class AmbiguityInstance:
    """A specific instance of ambiguity in text."""
    
    text: str
    ambiguity_type: AmbiguityType
    trigger_phrase: str
    position: int
    severity: float = 0.5
    confidence: float = 0.5
    context: str = ""
    interpretation_range: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert the ambiguity instance to a dictionary for serialization.

        Returns:
            dict: A dictionary containing all ambiguity instance attributes,
                with the ambiguity_type converted to its string value.
        """
        return {
            'text': self.text,
            'ambiguity_type': self.ambiguity_type.value,
            'trigger_phrase': self.trigger_phrase,
            'position': self.position,
            'severity': self.severity,
            'confidence': self.confidence,
            'context': self.context,
            'interpretation_range': self.interpretation_range
        }


@dataclass
class AmbiguityReport:
    """Report of ambiguity analysis."""
    
    document_id: str
    jurisdiction: Optional[str]
    total_instances: int
    instances_by_type: dict[AmbiguityType, int]
    high_severity_count: int
    ambiguity_score: float  # 0-1, higher = more ambiguous
    instances: list[AmbiguityInstance]
    recommendations: list[str]
    
    def to_dict(self) -> dict:
        """Convert the ambiguity report to a dictionary for serialization.

        Returns:
            dict: A dictionary containing all report attributes, with
                ambiguity types converted to string values and instances
                converted to dictionaries.
        """
        return {
            'document_id': self.document_id,
            'jurisdiction': self.jurisdiction,
            'total_instances': self.total_instances,
            'instances_by_type': {k.value: v for k, v in self.instances_by_type.items()},
            'high_severity_count': self.high_severity_count,
            'ambiguity_score': self.ambiguity_score,
            'instances': [i.to_dict() for i in self.instances],
            'recommendations': self.recommendations
        }


class AmbiguityDetector:
    """
    Detects ambiguous language in regulatory text.
    
    Identifies vague standards, undefined terms, and other
    language that creates enforcement uncertainty.
    """
    
    # Vague standard phrases
    VAGUE_STANDARDS = {
        'reasonable': ('Reasonable under the circumstances', 0.6),
        'appropriate': ('Appropriate measures', 0.6),
        'adequate': ('Adequate safeguards', 0.6),
        'sufficient': ('Sufficient controls', 0.5),
        'material': ('Material change/impact', 0.7),
        'significant': ('Significant risk', 0.6),
        'substantial': ('Substantial compliance', 0.6),
        'promptly': ('Promptly notify', 0.7),
        'timely': ('Timely manner', 0.6),
        'reasonable time': ('Within a reasonable time', 0.7),
        'as soon as practicable': ('As soon as practicable', 0.6),
        'to the extent practicable': ('To the extent practicable', 0.6),
        'good faith': ('Good faith effort', 0.5),
        'best efforts': ('Best efforts', 0.5),
        'commercially reasonable': ('Commercially reasonable efforts', 0.5),
        'duly': ('Duly authorized', 0.4),
        'properly': ('Properly maintained', 0.5),
        'as needed': ('As needed basis', 0.6),
        'as appropriate': ('As appropriate', 0.6),
        'in the ordinary course': ('In the ordinary course of business', 0.5),
    }
    
    # Scope-unclear phrases
    SCOPE_UNCLEAR_PATTERNS = [
        (r'\b(?:may|might)\s+(?:include|apply)', 'Scope may include', 0.6),
        (r'\bincluding\s+but\s+not\s+limited\s+to\b', 'Non-exhaustive list', 0.5),
        (r'\bsuch\s+as\b', 'Exemplary list', 0.4),
        (r'\bother\s+(?:similar|related|applicable)\b', 'Undefined other items', 0.6),
        (r'\band\s+similar\b', 'Similar items undefined', 0.5),
        (r'\bor\s+otherwise\b', 'Catch-all provision', 0.6),
        (r'\bto\s+the\s+extent\s+(?:applicable|relevant)\b', 'Applicability unclear', 0.6),
    ]
    
    # Timing-unclear patterns
    TIMING_UNCLEAR_PATTERNS = [
        (r'\bpromptly\b', 'Promptly - timing unspecified', 0.7),
        (r'\bwithout\s+(?:undue\s+)?delay\b', 'Without delay - no timeframe', 0.6),
        (r'\bas\s+soon\s+as\s+(?:reasonably\s+)?(?:practicable|possible)\b', 'ASAP - no deadline', 0.7),
        (r'\bin\s+a\s+timely\s+(?:manner|fashion)\b', 'Timely - undefined', 0.7),
        (r'\bperiodically\b', 'Periodically - frequency unclear', 0.6),
        (r'\bfrom\s+time\s+to\s+time\b', 'From time to time - no schedule', 0.5),
        (r'\bregularly\b', 'Regularly - frequency unclear', 0.5),
    ]
    
    # Threshold-unclear patterns
    THRESHOLD_UNCLEAR_PATTERNS = [
        (r'\bmaterial(?:ly)?\b', 'Material threshold undefined', 0.7),
        (r'\bsignificant(?:ly)?\b', 'Significant threshold undefined', 0.6),
        (r'\bsubstantial(?:ly)?\b', 'Substantial threshold undefined', 0.6),
        (r'\bde\s+minimis\b', 'De minimis threshold unclear', 0.6),
        (r'\bexcessive\b', 'Excessive threshold undefined', 0.6),
        (r'\bunusual\b', 'Unusual threshold undefined', 0.5),
    ]
    
    def __init__(
        self,
        defined_terms: Optional[set[str]] = None,
        severity_threshold: float = 0.0
    ):
        """
        Initialize detector.
        
        Args:
            defined_terms: Set of terms that are defined in the document
            severity_threshold: Minimum severity to include in results
        """
        self.defined_terms = defined_terms or set()
        self.severity_threshold = severity_threshold
        
        # Compile patterns
        self._scope_patterns = [(re.compile(p, re.IGNORECASE), d, s) 
                                 for p, d, s in self.SCOPE_UNCLEAR_PATTERNS]
        self._timing_patterns = [(re.compile(p, re.IGNORECASE), d, s) 
                                  for p, d, s in self.TIMING_UNCLEAR_PATTERNS]
        self._threshold_patterns = [(re.compile(p, re.IGNORECASE), d, s) 
                                     for p, d, s in self.THRESHOLD_UNCLEAR_PATTERNS]
    
    def detect(
        self,
        text: str,
        document_id: str = "unknown",
        jurisdiction: Optional[str] = None
    ) -> AmbiguityReport:
        """
        Detect ambiguity in regulatory text.
        
        Args:
            text: Regulatory text to analyze
            document_id: Identifier for the document
            jurisdiction: Optional jurisdiction
            
        Returns:
            AmbiguityReport with all detected ambiguities
        """
        instances = []
        
        # Detect vague standards
        instances.extend(self._detect_vague_standards(text))
        
        # Detect scope ambiguity
        instances.extend(self._detect_pattern_ambiguity(
            text, self._scope_patterns, AmbiguityType.SCOPE_UNCLEAR
        ))
        
        # Detect timing ambiguity
        instances.extend(self._detect_pattern_ambiguity(
            text, self._timing_patterns, AmbiguityType.TIMING_UNCLEAR
        ))
        
        # Detect threshold ambiguity
        instances.extend(self._detect_pattern_ambiguity(
            text, self._threshold_patterns, AmbiguityType.THRESHOLD_UNCLEAR
        ))
        
        # Detect undefined terms
        instances.extend(self._detect_undefined_terms(text))
        
        # Filter by severity threshold
        instances = [i for i in instances if i.severity >= self.severity_threshold]
        
        # Sort by position
        instances = sorted(instances, key=lambda x: x.position)
        
        # Calculate statistics
        instances_by_type = {}
        for inst in instances:
            if inst.ambiguity_type not in instances_by_type:
                instances_by_type[inst.ambiguity_type] = 0
            instances_by_type[inst.ambiguity_type] += 1
        
        high_severity_count = sum(1 for i in instances if i.severity >= 0.7)
        
        # Calculate overall ambiguity score
        if instances:
            word_count = len(text.split())
            ambiguity_score = min(1.0, len(instances) / (word_count / 100))
        else:
            ambiguity_score = 0.0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(instances, instances_by_type)
        
        return AmbiguityReport(
            document_id=document_id,
            jurisdiction=jurisdiction,
            total_instances=len(instances),
            instances_by_type=instances_by_type,
            high_severity_count=high_severity_count,
            ambiguity_score=ambiguity_score,
            instances=instances,
            recommendations=recommendations
        )
    
    def _detect_vague_standards(self, text: str) -> list[AmbiguityInstance]:
        """Detect vague standard phrases in regulatory text.

        Scans the text for common vague terms like "reasonable", "appropriate",
        and "material" that create interpretation uncertainty.

        Args:
            text: The regulatory text to analyze.

        Returns:
            list[AmbiguityInstance]: A list of detected vague standard instances,
                each containing the matched phrase, context, and severity.
        """
        instances = []
        text_lower = text.lower()
        
        for keyword, (description, severity) in self.VAGUE_STANDARDS.items():
            pattern = re.compile(rf'\b{re.escape(keyword.lower())}\b', re.IGNORECASE)
            
            for match in pattern.finditer(text_lower):
                # Get context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                instances.append(AmbiguityInstance(
                    text=match.group(),
                    ambiguity_type=AmbiguityType.VAGUE_STANDARD,
                    trigger_phrase=description,
                    position=match.start(),
                    severity=severity,
                    confidence=0.8,
                    context=context,
                    interpretation_range=[
                        "Conservative: Most restrictive interpretation",
                        "Moderate: Industry standard interpretation",
                        "Liberal: Least restrictive interpretation"
                    ]
                ))
        
        return instances
    
    def _detect_pattern_ambiguity(
        self,
        text: str,
        patterns: list[tuple[re.Pattern, str, float]],
        ambiguity_type: AmbiguityType
    ) -> list[AmbiguityInstance]:
        """Detect ambiguity in text using regex patterns.

        Args:
            text: The regulatory text to analyze.
            patterns: A list of tuples containing (compiled regex pattern,
                description string, severity float).
            ambiguity_type: The type of ambiguity being detected.

        Returns:
            list[AmbiguityInstance]: A list of detected ambiguity instances
                matching the provided patterns.
        """
        instances = []
        
        for pattern, description, severity in patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                instances.append(AmbiguityInstance(
                    text=match.group(),
                    ambiguity_type=ambiguity_type,
                    trigger_phrase=description,
                    position=match.start(),
                    severity=severity,
                    confidence=0.7,
                    context=context
                ))
        
        return instances
    
    def _detect_undefined_terms(self, text: str) -> list[AmbiguityInstance]:
        """Detect potentially undefined terms in the regulatory text.

        Identifies quoted terms that may require definitions but are not
        present in the defined_terms set. Skips terms that appear to be
        definitions themselves.

        Args:
            text: The regulatory text to analyze.

        Returns:
            list[AmbiguityInstance]: A list of detected undefined term instances.
        """
        instances = []
        
        # Look for quoted terms that might need definitions
        quoted_pattern = re.compile(r'"([^"]{2,50})"')
        
        for match in quoted_pattern.finditer(text):
            term = match.group(1)
            term_lower = term.lower()
            
            # Skip if it's a defined term
            if term_lower in {t.lower() for t in self.defined_terms}:
                continue
            
            # Skip common phrases that aren't terms
            skip_phrases = {'and', 'or', 'the', 'a', 'an', 'means', 'shall'}
            if term_lower in skip_phrases:
                continue
            
            # Check if it looks like a definition
            after_text = text[match.end():match.end() + 20].lower()
            if 'means' in after_text or 'shall mean' in after_text:
                continue
            
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]
            
            instances.append(AmbiguityInstance(
                text=term,
                ambiguity_type=AmbiguityType.UNDEFINED_TERM,
                trigger_phrase=f"Potentially undefined term: {term}",
                position=match.start(),
                severity=0.5,
                confidence=0.5,
                context=context
            ))
        
        return instances
    
    def _generate_recommendations(
        self,
        instances: list[AmbiguityInstance],
        by_type: dict[AmbiguityType, int]
    ) -> list[str]:
        """Generate recommendations based on ambiguity analysis results.

        Produces actionable recommendations for addressing detected ambiguities,
        including legal review guidance and type-specific suggestions.

        Args:
            instances: The list of all detected ambiguity instances.
            by_type: A dictionary mapping ambiguity types to their occurrence counts.

        Returns:
            list[str]: A list of recommendation strings for addressing
                the detected ambiguities.
        """
        recommendations = []
        
        if not instances:
            recommendations.append("No significant ambiguity detected")
            return recommendations
        
        # Always emphasize legal review
        recommendations.append(
            "IMPORTANT: This analysis identifies potential ambiguity but does not provide legal advice. "
            "Consult qualified legal counsel for interpretation guidance."
        )
        
        # Type-specific recommendations
        if by_type.get(AmbiguityType.VAGUE_STANDARD, 0) > 3:
            recommendations.append(
                "Multiple vague standards detected. Consider adopting conservative interpretations "
                "and documenting compliance rationale."
            )
        
        if by_type.get(AmbiguityType.TIMING_UNCLEAR, 0) > 2:
            recommendations.append(
                "Timing requirements are ambiguous. Seek clarification from regulators or "
                "adopt most restrictive reasonable timeframes."
            )
        
        if by_type.get(AmbiguityType.THRESHOLD_UNCLEAR, 0) > 2:
            recommendations.append(
                "Materiality/threshold definitions are unclear. Document your interpretation "
                "methodology and seek legal review."
            )
        
        high_severity = sum(1 for i in instances if i.severity >= 0.7)
        if high_severity > 5:
            recommendations.append(
                f"HIGH PRIORITY: {high_severity} high-severity ambiguities detected. "
                "Prioritize legal review of these items."
            )
        
        return recommendations
    
    def get_ambiguity_ranking(self, instances: list[AmbiguityInstance]) -> list[AmbiguityInstance]:
        """Rank ambiguities by severity for prioritization.

        Sorts ambiguity instances in descending order by severity first,
        then by confidence as a secondary sort key.

        Args:
            instances: The list of ambiguity instances to rank.

        Returns:
            list[AmbiguityInstance]: The sorted list of ambiguity instances,
                with highest severity and confidence items first.
        """
        return sorted(instances, key=lambda x: (-x.severity, -x.confidence))
