"""
Text normalization for regulatory documents.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizedText:
    """Represents normalized regulatory text."""
    
    original: str
    normalized: str
    sections: list[dict]
    word_count: int
    sentence_count: int


class TextNormalizer:
    """
    Normalizes regulatory text for consistent analysis.
    
    Handles:
    - Unicode normalization
    - Whitespace standardization
    - Section/article extraction
    - Legal citation normalization
    """
    
    # Common section header patterns
    SECTION_PATTERNS = [
        r'(?:^|\n)(?:Section|SECTION|§)\s*(\d+(?:\.\d+)*)',
        r'(?:^|\n)(?:Article|ARTICLE)\s*(\d+(?:\.\d+)*)',
        r'(?:^|\n)(?:Rule|RULE)\s*(\d+(?:\.\d+)*)',
        r'(?:^|\n)(?:Part|PART)\s*(\d+(?:\.\d+)*)',
        r'(?:^|\n)(\d+(?:\.\d+)*)\s*[.:]',
    ]
    
    # Legal citation patterns
    CITATION_PATTERNS = [
        (r'\bU\.S\.C\.', 'USC'),
        (r'\bC\.F\.R\.', 'CFR'),
        (r'\bFed\.\s*Reg\.', 'FedReg'),
        (r'\bS\.E\.C\.', 'SEC'),
    ]
    
    def __init__(
        self,
        lowercase: bool = False,
        remove_citations: bool = False,
        preserve_structure: bool = True
    ):
        """Initialize the TextNormalizer.

        Args:
            lowercase: If True, convert all text to lowercase.
            remove_citations: If True, remove citation references from text.
            preserve_structure: If True, maintain paragraph and section structure.
        """
        self.lowercase = lowercase
        self.remove_citations = remove_citations
        self.preserve_structure = preserve_structure
    
    def normalize(self, text: str) -> NormalizedText:
        """
        Normalize regulatory text.
        
        Args:
            text: Raw regulatory text
            
        Returns:
            NormalizedText with normalized content and metadata
        """
        original = text
        
        # Unicode normalization (NFKC for compatibility)
        normalized = unicodedata.normalize('NFKC', text)
        
        # Standardize line endings
        normalized = normalized.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace while preserving paragraph structure
        normalized = self._normalize_whitespace(normalized)
        
        # Normalize legal citations
        normalized = self._normalize_citations(normalized)
        
        # Extract sections
        sections = self._extract_sections(normalized)
        
        # Optional lowercase
        if self.lowercase:
            normalized = normalized.lower()
        
        # Count statistics
        word_count = len(normalized.split())
        sentence_count = len(re.findall(r'[.!?]+', normalized))
        
        return NormalizedText(
            original=original,
            normalized=normalized,
            sections=sections,
            word_count=word_count,
            sentence_count=sentence_count
        )
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace while preserving paragraph structure.

        Args:
            text: Input text with potentially irregular whitespace.

        Returns:
            Text with standardized whitespace (single spaces, double newlines
            for paragraphs).
        """
        # Replace multiple spaces with single space
        text = re.sub(r'[^\S\n]+', ' ', text)
        
        # Normalize multiple newlines to double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _normalize_citations(self, text: str) -> str:
        """Normalize legal citations for consistency.

        Converts abbreviations like U.S.C. to USC, C.F.R. to CFR, etc.
        Optionally removes citation references if remove_citations is True.

        Args:
            text: Input text containing legal citations.

        Returns:
            Text with normalized citation formats.
        """
        for pattern, replacement in self.CITATION_PATTERNS:
            text = re.sub(pattern, replacement, text)
        
        if self.remove_citations:
            # Remove common citation formats
            text = re.sub(r'\[\d+\]', '', text)
            text = re.sub(r'\(\d{4}\)', '', text)
        
        return text
    
    def _extract_sections(self, text: str) -> list[dict]:
        """Extract section structure from text.

        Identifies sections, articles, rules, and parts using common
        regulatory document patterns.

        Args:
            text: Normalized regulatory text.

        Returns:
            List of section dictionaries containing:
                - id: Section identifier (e.g., "1.2.3")
                - start: Character position where section starts
                - end: Character position where section ends
                - content: Truncated content (max 500 chars)
                - full_content: Complete section content
        """
        sections = []
        
        for pattern in self.SECTION_PATTERNS:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            
            for i, match in enumerate(matches):
                section_id = match.group(1)
                start = match.end()
                
                # End is either next section or end of text
                if i + 1 < len(matches):
                    end = matches[i + 1].start()
                else:
                    end = len(text)
                
                content = text[start:end].strip()
                
                sections.append({
                    'id': section_id,
                    'start': match.start(),
                    'end': end,
                    'content': content[:500] + '...' if len(content) > 500 else content,
                    'full_content': content
                })
        
        # Sort by position and deduplicate
        sections = sorted(sections, key=lambda x: x['start'])
        return self._deduplicate_sections(sections)
    
    def _deduplicate_sections(self, sections: list[dict]) -> list[dict]:
        """Remove overlapping section extractions.

        When multiple patterns match the same text region, keeps the most
        specific section (longest ID) or non-overlapping sections.

        Args:
            sections: List of section dictionaries sorted by start position.

        Returns:
            Deduplicated list of non-overlapping sections.
        """
        if not sections:
            return []
        
        deduplicated = [sections[0]]
        
        for section in sections[1:]:
            last = deduplicated[-1]
            # If this section starts after the last one ends, include it
            if section['start'] >= last['end']:
                deduplicated.append(section)
            # If this section is more specific (longer ID), replace
            elif len(section['id']) > len(last['id']):
                deduplicated[-1] = section
        
        return deduplicated
    
    def extract_definitions(self, text: str) -> list[dict]:
        """Extract defined terms from regulatory text.

        Looks for patterns like:
            - "term" means ...
            - "term" shall mean ...
            - As used in this section, "term" refers to ...

        Args:
            text: Regulatory text to search for definitions.

        Returns:
            List of definition dictionaries containing:
                - term: The defined term
                - context: Surrounding text (up to 200 chars after match)
                - position: Character position of the definition
        """
        definitions = []
        
        patterns = [
            r'"([^"]+)"\s+(?:means|shall mean|refers to|is defined as)',
            r'"([^"]+)"\s+has the meaning',
            r'(?:the term|The term)\s+"([^"]+)"',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                term = match.group(1)
                # Get context (100 chars after the match)
                context_start = match.start()
                context_end = min(match.end() + 200, len(text))
                context = text[context_start:context_end]
                
                definitions.append({
                    'term': term,
                    'context': context,
                    'position': match.start()
                })
        
        return definitions
