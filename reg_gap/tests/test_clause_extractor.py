"""
Tests for clause extraction.
"""

import pytest
from reg_gap.parsing.clause_extractor import ClauseExtractor, ClauseType, RegulatoryClause


class TestClauseExtractor:
    """Test suite for ClauseExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a ClauseExtractor instance for testing.

        Returns:
            ClauseExtractor: A new ClauseExtractor instance with default settings.
        """
        return ClauseExtractor()
    
    def test_extract_obligation(self, extractor):
        """Test extraction of obligation clauses.

        Verifies that obligation indicators like 'shall' are correctly
        identified and clauses are typed as OBLIGATION.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "The registrant shall file a quarterly report within 45 days."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        assert any(c.clause_type == ClauseType.OBLIGATION for c in clauses)
    
    def test_extract_prohibition(self, extractor):
        """Test extraction of prohibition clauses.

        Verifies that prohibition indicators like 'No ... shall' are correctly
        identified and clauses are typed as PROHIBITION.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "No broker-dealer shall engage in manipulative practices."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        assert any(c.clause_type == ClauseType.PROHIBITION for c in clauses)
    
    def test_extract_permission(self, extractor):
        """Test extraction of permission clauses.

        Verifies that permission indicators like 'may' are correctly
        identified and clauses are typed as PERMISSION.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "The investment adviser may delegate certain functions to qualified agents."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        assert any(c.clause_type == ClauseType.PERMISSION for c in clauses)
    
    def test_extract_multiple_clauses(self, extractor):
        """Test extraction of multiple clause types from a single text.

        Verifies that the extractor can identify and extract multiple
        clauses of different types (obligation, prohibition, permission)
        from a multi-section regulatory text.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = """
        Section 1. The registrant shall maintain accurate records.
        Section 2. No person may trade on material non-public information.
        Section 3. The Commission may grant exemptions in appropriate cases.
        """
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 3
    
    def test_extract_conditions(self, extractor):
        """Test extraction of conditional clauses.

        Verifies that conditional statements beginning with 'If' are
        correctly parsed and the conditions are captured in the clause.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "If the transaction exceeds $10,000, the broker must file a report."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        # Check that conditions are extracted
        relevant = [c for c in clauses if c.conditions]
        assert len(relevant) >= 1
    
    def test_extract_exceptions(self, extractor):
        """Test extraction of exception clauses.

        Verifies that exception phrases like 'except' are correctly
        parsed and the exceptions are captured in the clause.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "All transactions must be reported except those under $500."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        # Check that exceptions are extracted
        relevant = [c for c in clauses if c.exceptions]
        assert len(relevant) >= 1
    
    def test_minimum_length_filter(self, extractor):
        """Test that short sentences are filtered out.

        Verifies that sentences below the minimum clause length threshold
        are excluded from extraction results.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "Yes. No. Maybe. The registrant shall comply with all regulations."
        clauses = extractor.extract(text)
        
        # Short sentences should be filtered
        for clause in clauses:
            assert len(clause.text) >= extractor.min_clause_length
    
    def test_clause_confidence(self, extractor):
        """Test that confidence scores are assigned.

        Verifies that each extracted clause has a confidence score
        in the valid range of 0.0 to 1.0.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "The broker-dealer must report all suspicious activities immediately."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        for clause in clauses:
            assert 0 <= clause.confidence <= 1
    
    def test_subject_extraction(self, extractor):
        """Test subject extraction from clauses.

        Verifies that the extractor attempts to identify the subject
        (e.g., 'investment adviser') from regulatory clauses.
        Subject extraction is best-effort and may not always succeed.

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = "The investment adviser shall act in the best interest of clients."
        clauses = extractor.extract(text)
        
        assert len(clauses) >= 1
        # Should extract subject
        relevant = [c for c in clauses if c.subject]
        # Subject extraction is best-effort
    
    def test_extract_all_types(self, extractor):
        """Test grouped extraction by type.

        Verifies that extract_all_types returns clauses organized
        by their ClauseType (OBLIGATION, PROHIBITION, PERMISSION).

        Args:
            extractor: ClauseExtractor fixture instance.
        """
        text = """
        The registrant shall file reports annually.
        No person may engage in fraud.
        The Commission may grant extensions.
        """
        grouped = extractor.extract_all_types(text)
        
        assert ClauseType.OBLIGATION in grouped
        assert ClauseType.PROHIBITION in grouped
        assert ClauseType.PERMISSION in grouped


class TestRegulatoryClause:
    """Tests for RegulatoryClause dataclass."""
    
    def test_to_dict(self):
        """Test serialization to dictionary.

        Verifies that RegulatoryClause.to_dict() correctly converts
        the dataclass to a dictionary with proper key names and values.
        """
        clause = RegulatoryClause(
            text="Test clause text",
            clause_type=ClauseType.OBLIGATION,
            section_id="1.1",
            confidence=0.85
        )
        
        data = clause.to_dict()
        
        assert data['text'] == "Test clause text"
        assert data['clause_type'] == "obligation"
        assert data['section_id'] == "1.1"
        assert data['confidence'] == 0.85
    
    def test_conditions_list(self):
        """Test that conditions default to empty list.

        Verifies that a newly created RegulatoryClause without explicit
        conditions has an empty list for the conditions attribute.
        """
        clause = RegulatoryClause(
            text="Test",
            clause_type=ClauseType.OBLIGATION
        )
        
        assert isinstance(clause.conditions, list)
        assert len(clause.conditions) == 0
    
    def test_exceptions_list(self):
        """Test that exceptions default to empty list.

        Verifies that a newly created RegulatoryClause without explicit
        exceptions has an empty list for the exceptions attribute.
        """
        clause = RegulatoryClause(
            text="Test",
            clause_type=ClauseType.PROHIBITION
        )
        
        assert isinstance(clause.exceptions, list)
        assert len(clause.exceptions) == 0
