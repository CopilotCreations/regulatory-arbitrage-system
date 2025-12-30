#!/usr/bin/env python3
"""
RegulatoryGapAnalyzer CLI

Command-line interface for regulatory gap analysis.

Usage:
    python -m reg_gap.cli analyze <document_path> --jurisdiction <code>
    python -m reg_gap.cli compare <doc1> <doc2> --jurisdictions <j1> <j2>
    python -m reg_gap.cli report <output_path>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .ingestion import UniversalLoader, TextNormalizer
from .parsing import ClauseExtractor, EntityRecognizer, DefinitionExtractor
from .comparison import SemanticDiff, JurisdictionalComparator, AmbiguityDetector
from .comparison.jurisdictional import JurisdictionProfile
from .risk import EnforcementModel, SeverityAssessor, ConfidenceBounds
from .reports import ReportGenerator, Visualizer


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="reg_gap",
        description="RegulatoryGapAnalyzer - Identify regulatory ambiguity and divergence",
        epilog=(
            "DISCLAIMER: This tool provides analysis for informational purposes only. "
            "It does not constitute legal advice. Consult qualified legal counsel "
            "before making compliance decisions."
        )
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a single regulatory document"
    )
    analyze_parser.add_argument(
        "document",
        type=str,
        help="Path to the regulatory document"
    )
    analyze_parser.add_argument(
        "--jurisdiction", "-j",
        type=str,
        required=True,
        help="Jurisdiction code (e.g., US-SEC, EU-MiFID)"
    )
    analyze_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: stdout)"
    )
    analyze_parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown", "text"],
        default="text",
        help="Output format"
    )
    
    # Compare command
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two regulatory documents"
    )
    compare_parser.add_argument(
        "document1",
        type=str,
        help="Path to first document"
    )
    compare_parser.add_argument(
        "document2",
        type=str,
        help="Path to second document"
    )
    compare_parser.add_argument(
        "--jurisdictions", "-j",
        nargs=2,
        required=True,
        help="Jurisdiction codes for each document"
    )
    compare_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path"
    )
    compare_parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown", "text"],
        default="text",
        help="Output format"
    )
    
    # Report command
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a full analysis report"
    )
    report_parser.add_argument(
        "documents",
        nargs="+",
        type=str,
        help="Paths to regulatory documents"
    )
    report_parser.add_argument(
        "--jurisdictions", "-j",
        nargs="+",
        required=True,
        help="Jurisdiction codes (one per document)"
    )
    report_parser.add_argument(
        "--output", "-o",
        type=str,
        required=True,
        help="Output file path"
    )
    report_parser.add_argument(
        "--format", "-f",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format"
    )
    
    # Demo command for testing
    demo_parser = subparsers.add_parser(
        "demo",
        help="Run a demo analysis with synthetic data"
    )
    demo_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path"
    )
    
    return parser


def analyze_document(args) -> int:
    """Analyze a single regulatory document."""
    print(f"Analyzing: {args.document}")
    print(f"Jurisdiction: {args.jurisdiction}")
    print("-" * 50)
    
    # Load document
    loader = UniversalLoader()
    try:
        doc = loader.load(args.document, args.jurisdiction)
    except FileNotFoundError:
        print(f"Error: File not found: {args.document}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Normalize text
    normalizer = TextNormalizer()
    normalized = normalizer.normalize(doc.content)
    
    # Extract clauses
    clause_extractor = ClauseExtractor()
    clauses = clause_extractor.extract(normalized.normalized)
    
    # Extract definitions
    def_extractor = DefinitionExtractor()
    definitions = def_extractor.extract(
        normalized.normalized,
        source_document=args.document,
        jurisdiction=args.jurisdiction
    )
    
    # Detect ambiguity
    defined_terms = {d.term for d in definitions}
    ambiguity_detector = AmbiguityDetector(defined_terms=defined_terms)
    ambiguity_report = ambiguity_detector.detect(
        normalized.normalized,
        document_id=args.document,
        jurisdiction=args.jurisdiction
    )
    
    # Assess severity
    severity_assessor = SeverityAssessor()
    
    # Build results
    results = {
        "document": args.document,
        "jurisdiction": args.jurisdiction,
        "statistics": {
            "word_count": normalized.word_count,
            "sentence_count": normalized.sentence_count,
            "clause_count": len(clauses),
            "definition_count": len(definitions),
            "section_count": len(normalized.sections)
        },
        "clauses": {
            "obligations": len([c for c in clauses if c.clause_type.value == "obligation"]),
            "prohibitions": len([c for c in clauses if c.clause_type.value == "prohibition"]),
            "permissions": len([c for c in clauses if c.clause_type.value == "permission"]),
            "conditions": len([c for c in clauses if c.clause_type.value == "condition"])
        },
        "ambiguity": {
            "total_instances": ambiguity_report.total_instances,
            "high_severity_count": ambiguity_report.high_severity_count,
            "ambiguity_score": round(ambiguity_report.ambiguity_score, 3),
            "top_issues": [
                {
                    "type": inst.ambiguity_type.value,
                    "phrase": inst.trigger_phrase,
                    "severity": inst.severity
                }
                for inst in sorted(ambiguity_report.instances, key=lambda x: -x.severity)[:5]
            ]
        },
        "recommendations": ambiguity_report.recommendations,
        "disclaimer": (
            "This analysis is for informational purposes only. "
            "Consult qualified legal counsel before making compliance decisions."
        )
    }
    
    # Output results
    output = format_output(results, args.format)
    
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Results written to: {args.output}")
    else:
        print(output)
    
    return 0


def compare_documents(args) -> int:
    """Compare two regulatory documents."""
    print(f"Comparing documents:")
    print(f"  1. {args.document1} ({args.jurisdictions[0]})")
    print(f"  2. {args.document2} ({args.jurisdictions[1]})")
    print("-" * 50)
    
    loader = UniversalLoader()
    normalizer = TextNormalizer()
    clause_extractor = ClauseExtractor()
    def_extractor = DefinitionExtractor()
    
    # Load and process both documents
    docs = []
    profiles = []
    
    for doc_path, jurisdiction in zip(
        [args.document1, args.document2],
        args.jurisdictions
    ):
        try:
            doc = loader.load(doc_path, jurisdiction)
            normalized = normalizer.normalize(doc.content)
            clauses = clause_extractor.extract(normalized.normalized)
            definitions = def_extractor.extract(
                normalized.normalized,
                source_document=doc_path,
                jurisdiction=jurisdiction
            )
            
            profile = JurisdictionProfile(
                jurisdiction=jurisdiction,
                clauses=clauses,
                definitions=definitions
            )
            
            docs.append(doc)
            profiles.append(profile)
            
        except FileNotFoundError:
            print(f"Error: File not found: {doc_path}", file=sys.stderr)
            return 1
    
    # Compare
    comparator = JurisdictionalComparator()
    gaps = comparator.compare(profiles[0], profiles[1])
    
    # Generate visualizations
    visualizer = Visualizer()
    gap_matrix = {(args.jurisdictions[0], args.jurisdictions[1]): gaps}
    
    # Build results
    results = {
        "comparison": {
            "jurisdiction_a": args.jurisdictions[0],
            "jurisdiction_b": args.jurisdictions[1]
        },
        "summary": {
            "total_gaps": len(gaps),
            "high_severity_gaps": len([g for g in gaps if g.severity >= 0.7]),
            "requires_review": len([g for g in gaps if g.requires_legal_review])
        },
        "gaps_by_type": {},
        "top_gaps": [],
        "disclaimer": (
            "This comparison is for informational purposes only. "
            "All gaps require qualified legal review before any compliance decisions."
        )
    }
    
    # Count by type
    for gap in gaps:
        gt = gap.gap_type.value
        results["gaps_by_type"][gt] = results["gaps_by_type"].get(gt, 0) + 1
    
    # Top gaps
    for gap in sorted(gaps, key=lambda g: -g.severity)[:10]:
        results["top_gaps"].append({
            "type": gap.gap_type.value,
            "description": gap.description,
            "severity": round(gap.severity, 3),
            "recommendations": gap.recommendations
        })
    
    # Output
    output = format_output(results, args.format)
    
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Results written to: {args.output}")
    else:
        print(output)
    
    return 0


def generate_report(args) -> int:
    """Generate a full analysis report."""
    if len(args.documents) != len(args.jurisdictions):
        print("Error: Number of documents must match number of jurisdictions", file=sys.stderr)
        return 1
    
    print(f"Generating report for {len(args.documents)} documents...")
    
    loader = UniversalLoader()
    normalizer = TextNormalizer()
    clause_extractor = ClauseExtractor()
    def_extractor = DefinitionExtractor()
    
    profiles = []
    all_clauses = []
    all_definitions = []
    all_ambiguities = []
    
    for doc_path, jurisdiction in zip(args.documents, args.jurisdictions):
        try:
            print(f"  Processing: {doc_path} ({jurisdiction})")
            
            doc = loader.load(doc_path, jurisdiction)
            normalized = normalizer.normalize(doc.content)
            clauses = clause_extractor.extract(normalized.normalized)
            definitions = def_extractor.extract(
                normalized.normalized,
                source_document=doc_path,
                jurisdiction=jurisdiction
            )
            
            # Detect ambiguity
            defined_terms = {d.term for d in definitions}
            detector = AmbiguityDetector(defined_terms=defined_terms)
            amb_report = detector.detect(
                normalized.normalized,
                document_id=doc_path,
                jurisdiction=jurisdiction
            )
            
            profile = JurisdictionProfile(
                jurisdiction=jurisdiction,
                clauses=clauses,
                definitions=definitions
            )
            
            profiles.append(profile)
            all_clauses.extend(clauses)
            all_definitions.extend(definitions)
            all_ambiguities.append(amb_report)
            
        except FileNotFoundError:
            print(f"Error: File not found: {doc_path}", file=sys.stderr)
            return 1
    
    # Compare all pairs
    comparator = JurisdictionalComparator()
    gap_matrix = comparator.generate_gap_matrix(profiles)
    
    # Model enforcement
    enforcement_model = EnforcementModel()
    scenarios = []
    for clause in all_clauses[:50]:  # Limit for performance
        scenario = enforcement_model.model_clause_risk(clause)
        scenarios.append(scenario)
    
    # Assess severity
    severity_assessor = SeverityAssessor()
    severity_ratings = []
    for (_, _), gaps in gap_matrix.items():
        for gap in gaps[:20]:  # Limit for performance
            rating = severity_assessor.assess_gap(gap)
            severity_ratings.append(rating)
    
    # Generate report
    report_generator = ReportGenerator()
    report = report_generator.generate_compliance_report(
        jurisdictions=args.jurisdictions,
        gap_matrix=gap_matrix,
        ambiguity_reports=all_ambiguities,
        enforcement_scenarios=scenarios,
        severity_ratings=severity_ratings,
        document_count=len(args.documents),
        clause_count=len(all_clauses)
    )
    
    # Format output
    if args.format == "markdown":
        output = report_generator.generate_markdown_report(report)
    else:
        output = report.to_json()
    
    Path(args.output).write_text(output, encoding='utf-8')
    print(f"Report written to: {args.output}")
    
    return 0


def run_demo(args) -> int:
    """Run a demo with synthetic regulatory data."""
    print("Running RegulatoryGapAnalyzer Demo")
    print("=" * 50)
    
    # Synthetic regulation text
    regulation_us = """
    Section 1. Definitions
    "Covered Person" means any registered broker-dealer or investment adviser.
    "Material Change" means any change that would reasonably be expected to affect 
    the investment decision of a prudent investor.
    
    Section 2. Disclosure Requirements
    2.1 Every covered person shall provide written disclosure of all material 
    conflicts of interest to customers within 30 days of discovery.
    
    2.2 No covered person shall engage in any transaction that creates a material 
    conflict of interest without prior written consent from the customer.
    
    2.3 Covered persons may, at their discretion, provide additional disclosures 
    as appropriate under the circumstances.
    
    Section 3. Record Keeping
    3.1 All covered persons must maintain adequate records of customer communications 
    for a period of not less than 5 years.
    
    3.2 Records shall be made available to the Commission promptly upon request.
    """
    
    regulation_eu = """
    Article 1. Scope and Definitions
    "Investment Firm" shall mean any legal person that provides investment services.
    "Significant Change" refers to changes materially affecting client portfolios.
    
    Article 2. Client Information Obligations
    2.1 Investment firms are required to disclose all significant conflicts of 
    interest to clients without delay.
    
    2.2 Investment firms must not enter into transactions creating conflicts 
    unless the client has provided informed consent in advance.
    
    2.3 Firms should provide supplementary information where reasonably necessary.
    
    Article 3. Documentation Requirements
    3.1 Firms shall maintain comprehensive records of all client interactions 
    for a minimum period of 7 years.
    
    3.2 Records must be provided to competent authorities within 10 business days 
    of a formal request.
    """
    
    print("\nAnalyzing synthetic US regulation...")
    
    # Process US regulation
    normalizer = TextNormalizer()
    clause_extractor = ClauseExtractor()
    def_extractor = DefinitionExtractor()
    
    us_normalized = normalizer.normalize(regulation_us)
    us_clauses = clause_extractor.extract(us_normalized.normalized)
    us_definitions = def_extractor.extract(us_normalized.normalized, jurisdiction="US-SEC")
    
    print(f"  - Extracted {len(us_clauses)} clauses")
    print(f"  - Found {len(us_definitions)} definitions")
    
    print("\nAnalyzing synthetic EU regulation...")
    
    eu_normalized = normalizer.normalize(regulation_eu)
    eu_clauses = clause_extractor.extract(eu_normalized.normalized)
    eu_definitions = def_extractor.extract(eu_normalized.normalized, jurisdiction="EU-MiFID")
    
    print(f"  - Extracted {len(eu_clauses)} clauses")
    print(f"  - Found {len(eu_definitions)} definitions")
    
    # Create profiles
    us_profile = JurisdictionProfile(
        jurisdiction="US-SEC",
        clauses=us_clauses,
        definitions=us_definitions
    )
    
    eu_profile = JurisdictionProfile(
        jurisdiction="EU-MiFID",
        clauses=eu_clauses,
        definitions=eu_definitions
    )
    
    # Compare
    print("\nComparing jurisdictions...")
    comparator = JurisdictionalComparator()
    gaps = comparator.compare(us_profile, eu_profile)
    
    print(f"\n  Total gaps identified: {len(gaps)}")
    print(f"  High severity gaps: {len([g for g in gaps if g.severity >= 0.7])}")
    print(f"  Gaps requiring legal review: {len([g for g in gaps if g.requires_legal_review])}")
    
    # Detect ambiguity
    print("\nDetecting ambiguity...")
    detector = AmbiguityDetector()
    
    us_ambiguity = detector.detect(us_normalized.normalized, "US-Regulation", "US-SEC")
    eu_ambiguity = detector.detect(eu_normalized.normalized, "EU-Regulation", "EU-MiFID")
    
    print(f"  US regulation ambiguity score: {us_ambiguity.ambiguity_score:.3f}")
    print(f"  EU regulation ambiguity score: {eu_ambiguity.ambiguity_score:.3f}")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    visualizer = Visualizer()
    gap_matrix = {("US-SEC", "EU-MiFID"): gaps}
    
    heatmap = visualizer.generate_jurisdiction_heatmap(gap_matrix)
    print(visualizer.generate_ascii_heatmap(heatmap))
    
    # Generate ranking
    all_ambiguities = us_ambiguity.instances + eu_ambiguity.instances
    if all_ambiguities:
        ranking = visualizer.generate_ambiguity_ranking(all_ambiguities)
        print(visualizer.generate_ascii_ranking(ranking))
    
    # Summary
    print("\n" + "=" * 50)
    print("DEMO SUMMARY")
    print("=" * 50)
    print(f"Documents analyzed: 2 (synthetic)")
    print(f"Jurisdictions: US-SEC, EU-MiFID")
    print(f"Total clauses: {len(us_clauses) + len(eu_clauses)}")
    print(f"Total definitions: {len(us_definitions) + len(eu_definitions)}")
    print(f"Jurisdictional gaps: {len(gaps)}")
    print(f"Ambiguity instances: {len(all_ambiguities)}")
    
    print("\n⚠️  DISCLAIMER")
    print("-" * 50)
    print("This demo uses synthetic data for illustration purposes.")
    print("Real regulatory analysis requires qualified legal review.")
    print("This tool does not provide legal advice.")
    
    if args.output:
        # Save demo results
        results = {
            "demo": True,
            "jurisdictions": ["US-SEC", "EU-MiFID"],
            "gaps": [g.to_dict() for g in gaps],
            "us_ambiguity": us_ambiguity.to_dict(),
            "eu_ambiguity": eu_ambiguity.to_dict()
        }
        Path(args.output).write_text(json.dumps(results, indent=2, default=str), encoding='utf-8')
        print(f"\nDemo results saved to: {args.output}")
    
    return 0


def format_output(data: dict, format_type: str) -> str:
    """Format output data according to requested format."""
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)
    
    elif format_type == "markdown":
        lines = ["# Regulatory Analysis Results\n"]
        
        def dict_to_md(d: dict, level: int = 2) -> list:
            result = []
            for key, value in d.items():
                heading = "#" * level
                if isinstance(value, dict):
                    result.append(f"{heading} {key.replace('_', ' ').title()}\n")
                    result.extend(dict_to_md(value, level + 1))
                elif isinstance(value, list):
                    result.append(f"{heading} {key.replace('_', ' ').title()}\n")
                    for item in value:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                result.append(f"- **{k}**: {v}")
                            result.append("")
                        else:
                            result.append(f"- {item}")
                else:
                    result.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            return result
        
        lines.extend(dict_to_md(data))
        return "\n".join(lines)
    
    else:  # text
        lines = []
        
        def dict_to_text(d: dict, indent: int = 0) -> list:
            result = []
            prefix = "  " * indent
            for key, value in d.items():
                if isinstance(value, dict):
                    result.append(f"{prefix}{key.replace('_', ' ').upper()}:")
                    result.extend(dict_to_text(value, indent + 1))
                elif isinstance(value, list):
                    result.append(f"{prefix}{key.replace('_', ' ').upper()}:")
                    for item in value:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                result.append(f"{prefix}  - {k}: {v}")
                        else:
                            result.append(f"{prefix}  - {item}")
                else:
                    result.append(f"{prefix}{key.replace('_', ' ')}: {value}")
            return result
        
        lines.extend(dict_to_text(data))
        return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == "analyze":
        return analyze_document(args)
    elif args.command == "compare":
        return compare_documents(args)
    elif args.command == "report":
        return generate_report(args)
    elif args.command == "demo":
        return run_demo(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
