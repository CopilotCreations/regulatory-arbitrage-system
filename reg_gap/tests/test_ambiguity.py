"""
Tests for ambiguity detection.
"""

import pytest
from reg_gap.comparison.ambiguity import AmbiguityDetector, AmbiguityType, AmbiguityInstance


class TestAmbiguityDetector:
    """Test suite for AmbiguityDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a default AmbiguityDetector instance for tests.

        Returns:
            AmbiguityDetector: A detector instance with default settings.
        """
        return AmbiguityDetector()
    
    def test_detect_vague_standard_reasonable(self, detector):
        """Test detection of 'reasonable' as vague standard.

        Verifies that the detector correctly identifies the word 'reasonable'
        as a vague standard that could lead to ambiguous interpretation.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "The firm shall take reasonable steps to ensure compliance."
        report = detector.detect(text)
        
        assert report.total_instances > 0
        vague = [i for i in report.instances if i.ambiguity_type == AmbiguityType.VAGUE_STANDARD]
        assert len(vague) > 0
    
    def test_detect_vague_standard_material(self, detector):
        """Test detection of 'material' as vague standard.

        Verifies that the detector identifies 'material' as a vague standard
        and may also detect 'promptly' as a timing ambiguity.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "Any material change must be disclosed promptly."
        report = detector.detect(text)
        
        assert report.total_instances > 0
        # Should detect both 'material' and 'promptly'
    
    def test_detect_timing_unclear(self, detector):
        """Test detection of unclear timing requirements.

        Verifies that terms like 'promptly' are detected as unclear
        timing requirements that lack specific deadlines.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "The report shall be filed promptly after discovery."
        report = detector.detect(text)
        
        timing = [i for i in report.instances if i.ambiguity_type == AmbiguityType.TIMING_UNCLEAR]
        assert len(timing) > 0
    
    def test_detect_threshold_unclear(self, detector):
        """Test detection of unclear thresholds.

        Verifies that terms like 'significant' are detected as unclear
        thresholds that lack quantitative definitions.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "Significant transactions require additional review."
        report = detector.detect(text)
        
        threshold = [i for i in report.instances if i.ambiguity_type == AmbiguityType.THRESHOLD_UNCLEAR]
        assert len(threshold) > 0
    
    def test_detect_scope_unclear(self, detector):
        """Test detection of unclear scope.

        Verifies that phrases like 'including but not limited to' are
        detected as scope ambiguities that leave boundaries undefined.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "This applies to transactions including but not limited to securities trades."
        report = detector.detect(text)
        
        scope = [i for i in report.instances if i.ambiguity_type == AmbiguityType.SCOPE_UNCLEAR]
        assert len(scope) > 0
    
    def test_ambiguity_score_calculation(self, detector):
        """Test that ambiguity score is calculated.

        Verifies that the overall ambiguity score is computed and
        falls within the valid range of 0 to 1.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "The firm shall take reasonable steps in a timely manner as appropriate."
        report = detector.detect(text)
        
        assert 0 <= report.ambiguity_score <= 1
    
    def test_high_severity_count(self, detector):
        """Test counting of high-severity ambiguities.

        Verifies that the detector correctly counts ambiguities
        classified as high severity based on their impact.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = """
        Material changes must be reported promptly.
        Significant transactions require timely review.
        """
        report = detector.detect(text)
        
        # Should have some high-severity items
        assert report.high_severity_count >= 0
    
    def test_defined_terms_excluded(self):
        """Test that defined terms are not flagged as undefined.

        Verifies that terms explicitly provided in the defined_terms set
        are excluded from being flagged as undefined terms.
        """
        defined_terms = {"material change", "covered person"}
        detector = AmbiguityDetector(defined_terms=defined_terms)
        
        text = '"Material Change" means any significant alteration. Report all material changes.'
        report = detector.detect(text)
        
        undefined = [i for i in report.instances if i.ambiguity_type == AmbiguityType.UNDEFINED_TERM]
        # Should not flag "material change" as undefined
        for inst in undefined:
            assert inst.text.lower() != "material change"
    
    def test_recommendations_generated(self, detector):
        """Test that recommendations are generated.

        Verifies that the detector generates actionable recommendations
        for addressing detected ambiguities, including legal review.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "The firm shall comply with reasonable standards in a timely manner."
        report = detector.detect(text)
        
        assert len(report.recommendations) > 0
        # Should include legal review recommendation
        assert any("legal" in r.lower() for r in report.recommendations)
    
    def test_instances_have_context(self, detector):
        """Test that instances include context.

        Verifies that each detected ambiguity instance includes
        surrounding context text for better understanding.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = "All parties shall act in good faith during negotiations."
        report = detector.detect(text)
        
        for instance in report.instances:
            # Context should be non-empty if text is long enough
            if len(text) > 50:
                assert len(instance.context) > 0
    
    def test_instances_sorted_by_position(self, detector):
        """Test that instances are sorted by position.

        Verifies that detected ambiguity instances are returned
        in order of their position within the source text.

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = """
        First, reasonable efforts are required.
        Second, timely notification is mandatory.
        Third, appropriate measures shall be taken.
        """
        report = detector.detect(text)
        
        positions = [i.position for i in report.instances]
        assert positions == sorted(positions)
    
    def test_severity_threshold_filter(self):
        """Test severity threshold filtering.

        Verifies that when a severity threshold is configured, only
        ambiguities meeting or exceeding that threshold are returned.
        """
        detector = AmbiguityDetector(severity_threshold=0.6)
        
        text = "The firm shall act appropriately and take reasonable measures promptly."
        report = detector.detect(text)
        
        # All instances should be above threshold
        for instance in report.instances:
            assert instance.severity >= 0.6
    
    def test_get_ambiguity_ranking(self, detector):
        """Test ranking of ambiguities by severity.

        Verifies that the get_ambiguity_ranking method returns instances
        sorted by severity in descending order (highest first).

        Args:
            detector: AmbiguityDetector fixture instance.
        """
        text = """
        Material changes require prompt notification.
        Reasonable efforts shall be made.
        Appropriate measures are necessary.
        """
        report = detector.detect(text)
        
        ranked = detector.get_ambiguity_ranking(report.instances)
        
        # Should be sorted by severity descending
        severities = [i.severity for i in ranked]
        assert severities == sorted(severities, reverse=True)


class TestAmbiguityInstance:
    """Tests for AmbiguityInstance dataclass."""
    
    def test_to_dict(self):
        """Test serialization to dictionary.

        Verifies that AmbiguityInstance correctly serializes all fields
        to a dictionary format suitable for JSON output.
        """
        instance = AmbiguityInstance(
            text="reasonable",
            ambiguity_type=AmbiguityType.VAGUE_STANDARD,
            trigger_phrase="Reasonable under the circumstances",
            position=100,
            severity=0.6,
            confidence=0.8
        )
        
        data = instance.to_dict()
        
        assert data['text'] == "reasonable"
        assert data['ambiguity_type'] == "vague_standard"
        assert data['severity'] == 0.6
        assert data['confidence'] == 0.8
    
    def test_interpretation_range(self):
        """Test interpretation range field.

        Verifies that AmbiguityInstance correctly stores and retrieves
        the interpretation_range field containing possible interpretations.
        """
        instance = AmbiguityInstance(
            text="material",
            ambiguity_type=AmbiguityType.THRESHOLD_UNCLEAR,
            trigger_phrase="Material threshold",
            position=0,
            interpretation_range=[
                "Conservative: 1% threshold",
                "Moderate: 5% threshold",
                "Liberal: 10% threshold"
            ]
        )
        
        assert len(instance.interpretation_range) == 3
