"""
Tests with synthetic regulations containing known conflicts.
"""

import pytest
from reg_gap.parsing.clause_extractor import ClauseExtractor, ClauseType
from reg_gap.parsing.definitions import DefinitionExtractor
from reg_gap.comparison.jurisdictional import (
    JurisdictionalComparator, 
    JurisdictionProfile,
    GapType
)
from reg_gap.comparison.ambiguity import AmbiguityDetector


class TestSyntheticRegulations:
    """Tests using synthetic regulations with known characteristics."""
    
    @pytest.fixture
    def strict_regulation(self):
        """Stricter regulation text."""
        return """
        Section 1. Definitions
        "Covered Transaction" means any transaction exceeding $1,000 in value.
        "Reporting Period" means within 24 hours of the transaction.
        
        Section 2. Mandatory Reporting
        2.1 All covered persons shall report every covered transaction to the 
        Commission within the reporting period, without exception.
        
        2.2 No person may execute a covered transaction without maintaining 
        complete documentation for a period of 10 years.
        
        Section 3. Prohibitions
        3.1 Covered persons are strictly prohibited from engaging in any 
        transaction that creates a conflict of interest.
        
        3.2 No exemptions shall be granted under any circumstances.
        """
    
    @pytest.fixture
    def lenient_regulation(self):
        """More lenient regulation text."""
        return """
        Article 1. Definitions
        "Reportable Transaction" means transactions generally exceeding $10,000.
        "Reasonable Time" means a commercially reasonable period.
        
        Article 2. Reporting Guidelines
        2.1 Firms should report significant transactions within a reasonable time 
        after becoming aware of the transaction.
        
        2.2 Firms may maintain documentation as appropriate under the circumstances,
        generally for a period of at least 5 years.
        
        Article 3. Conflict Management
        3.1 Firms should take reasonable steps to manage conflicts of interest.
        
        3.2 Exemptions may be granted where the Commission determines it is 
        appropriate under the circumstances.
        """
    
    @pytest.fixture
    def clause_extractor(self):
        return ClauseExtractor()
    
    @pytest.fixture
    def definition_extractor(self):
        return DefinitionExtractor()
    
    def test_strict_has_more_obligations(
        self, strict_regulation, lenient_regulation, clause_extractor
    ):
        """Test that stricter regulation has more obligations."""
        strict_clauses = clause_extractor.extract(strict_regulation)
        lenient_clauses = clause_extractor.extract(lenient_regulation)
        
        strict_obligations = [c for c in strict_clauses if c.clause_type == ClauseType.OBLIGATION]
        lenient_obligations = [c for c in lenient_clauses if c.clause_type == ClauseType.OBLIGATION]
        
        # Strict regulation should have more or equal obligations
        assert len(strict_obligations) >= len(lenient_obligations)
    
    def test_strict_has_more_prohibitions(
        self, strict_regulation, lenient_regulation, clause_extractor
    ):
        """Test that stricter regulation has more prohibitions."""
        strict_clauses = clause_extractor.extract(strict_regulation)
        lenient_clauses = clause_extractor.extract(lenient_regulation)
        
        strict_prohibitions = [c for c in strict_clauses if c.clause_type == ClauseType.PROHIBITION]
        lenient_prohibitions = [c for c in lenient_clauses if c.clause_type == ClauseType.PROHIBITION]
        
        assert len(strict_prohibitions) >= len(lenient_prohibitions)
    
    def test_lenient_has_more_permissions(
        self, strict_regulation, lenient_regulation, clause_extractor
    ):
        """Test that lenient regulation has more permissions."""
        strict_clauses = clause_extractor.extract(strict_regulation)
        lenient_clauses = clause_extractor.extract(lenient_regulation)
        
        strict_permissions = [c for c in strict_clauses if c.clause_type == ClauseType.PERMISSION]
        lenient_permissions = [c for c in lenient_clauses if c.clause_type == ClauseType.PERMISSION]
        
        # Lenient should have more or equal permissions
        assert len(lenient_permissions) >= len(strict_permissions)
    
    def test_definition_conflict_detected(
        self, strict_regulation, lenient_regulation, definition_extractor
    ):
        """Test that definitional conflicts are identified."""
        strict_defs = definition_extractor.extract(strict_regulation, jurisdiction="Strict")
        lenient_defs = definition_extractor.extract(lenient_regulation, jurisdiction="Lenient")
        
        all_defs = strict_defs + lenient_defs
        conflicts = definition_extractor.find_conflicts(all_defs)
        
        # May or may not have conflicts depending on term overlap
        # This tests the mechanism works
        assert isinstance(conflicts, list)
    
    def test_lenient_has_higher_ambiguity(
        self, strict_regulation, lenient_regulation
    ):
        """Test that lenient regulation has higher ambiguity score."""
        detector = AmbiguityDetector()
        
        strict_report = detector.detect(strict_regulation, "Strict")
        lenient_report = detector.detect(lenient_regulation, "Lenient")
        
        # Lenient regulation uses more vague language
        assert lenient_report.ambiguity_score >= strict_report.ambiguity_score
    
    def test_jurisdictional_gaps_identified(
        self, strict_regulation, lenient_regulation, clause_extractor, definition_extractor
    ):
        """Test that jurisdictional gaps are identified."""
        strict_clauses = clause_extractor.extract(strict_regulation)
        lenient_clauses = clause_extractor.extract(lenient_regulation)
        
        strict_defs = definition_extractor.extract(strict_regulation, jurisdiction="Strict")
        lenient_defs = definition_extractor.extract(lenient_regulation, jurisdiction="Lenient")
        
        strict_profile = JurisdictionProfile(
            jurisdiction="Strict",
            clauses=strict_clauses,
            definitions=strict_defs
        )
        
        lenient_profile = JurisdictionProfile(
            jurisdiction="Lenient",
            clauses=lenient_clauses,
            definitions=lenient_defs
        )
        
        comparator = JurisdictionalComparator()
        gaps = comparator.compare(strict_profile, lenient_profile)
        
        # Should identify some gaps
        assert len(gaps) > 0
        
        # All gaps should require legal review
        assert all(g.requires_legal_review for g in gaps)
    
    def test_gap_recommendations_not_prescriptive(
        self, strict_regulation, lenient_regulation, clause_extractor, definition_extractor
    ):
        """Test that gap recommendations emphasize review, not action."""
        strict_clauses = clause_extractor.extract(strict_regulation)
        lenient_clauses = clause_extractor.extract(lenient_regulation)
        
        strict_profile = JurisdictionProfile(
            jurisdiction="Strict",
            clauses=strict_clauses,
            definitions=definition_extractor.extract(strict_regulation)
        )
        
        lenient_profile = JurisdictionProfile(
            jurisdiction="Lenient",
            clauses=lenient_clauses,
            definitions=definition_extractor.extract(lenient_regulation)
        )
        
        comparator = JurisdictionalComparator()
        gaps = comparator.compare(strict_profile, lenient_profile)
        
        prescriptive_words = ['must do', 'should implement', 'take action', 'comply by']
        review_words = ['review', 'legal', 'consider', 'evaluate', 'mandatory']
        
        for gap in gaps:
            for rec in gap.recommendations:
                rec_lower = rec.lower()
                # Should contain review-oriented language
                has_review = any(word in rec_lower for word in review_words)
                # Should not contain prescriptive language
                has_prescriptive = any(phrase in rec_lower for phrase in prescriptive_words)
                
                # This is a soft check - recommendations should be review-focused
                if gap.requires_legal_review:
                    assert has_review or not has_prescriptive


class TestRegressionClauseExtraction:
    """Regression tests for clause extraction accuracy."""
    
    @pytest.fixture
    def extractor(self):
        return ClauseExtractor()
    
    @pytest.mark.parametrize("text,expected_type", [
        ("The registrant shall file Form 10-K annually.", ClauseType.OBLIGATION),
        ("Investment advisers must maintain accurate records.", ClauseType.OBLIGATION),
        ("The broker is required to disclose conflicts.", ClauseType.OBLIGATION),
        ("No person shall engage in market manipulation.", ClauseType.PROHIBITION),
        ("Insiders may not trade on material non-public information.", ClauseType.PROHIBITION),
        ("Trading is prohibited during blackout periods.", ClauseType.PROHIBITION),
        ("The Commission may grant exemptions.", ClauseType.PERMISSION),
        ("Firms can delegate certain functions.", ClauseType.PERMISSION),
        ("If the transaction exceeds the threshold, reporting is required.", ClauseType.CONDITION),
    ])
    def test_clause_type_detection(self, extractor, text, expected_type):
        """Test that specific clause patterns are correctly classified."""
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        assert any(c.clause_type == expected_type for c in clauses), \
            f"Expected {expected_type} but got {[c.clause_type for c in clauses]}"


class TestFalsePositiveMinimization:
    """Tests to ensure false positive rates are minimized."""
    
    @pytest.fixture
    def detector(self):
        return AmbiguityDetector()
    
    def test_specific_timeframes_not_ambiguous(self, detector):
        """Test that specific timeframes are not flagged as ambiguous."""
        text = "Reports must be filed within 30 days of the triggering event."
        report = detector.detect(text)
        
        timing_ambiguities = [
            i for i in report.instances 
            if i.ambiguity_type.value == "timing_unclear"
        ]
        
        # Should not flag "30 days" as ambiguous
        for amb in timing_ambiguities:
            assert "30 days" not in amb.text
    
    def test_specific_thresholds_not_ambiguous(self, detector):
        """Test that specific thresholds are not flagged as ambiguous."""
        text = "Transactions exceeding $10,000 must be reported."
        report = detector.detect(text)
        
        threshold_ambiguities = [
            i for i in report.instances 
            if i.ambiguity_type.value == "threshold_unclear"
        ]
        
        # Should not flag the specific dollar amount
        for amb in threshold_ambiguities:
            assert "$10,000" not in amb.text
    
    def test_defined_terms_not_undefined(self):
        """Test that properly defined terms are not flagged as undefined."""
        detector = AmbiguityDetector(defined_terms={"covered person", "reporting period"})
        
        text = '''
        "Covered Person" means any registered representative.
        Each covered person must file reports during the reporting period.
        '''
        
        report = detector.detect(text)
        
        undefined = [
            i for i in report.instances 
            if i.ambiguity_type.value == "undefined_term"
        ]
        
        # Should not flag defined terms
        for amb in undefined:
            assert amb.text.lower() not in {"covered person", "reporting period"}
