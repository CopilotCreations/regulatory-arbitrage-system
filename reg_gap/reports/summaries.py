"""
Report generation for regulatory gap analysis.

Generates structured reports that:
- Summarize findings
- Highlight areas requiring legal review
- Provide actionable (but non-prescriptive) insights
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from ..comparison.jurisdictional import JurisdictionalGap, GapType
from ..comparison.ambiguity import AmbiguityReport, AmbiguityInstance
from ..risk.enforcement_model import EnforcementScenario
from ..risk.severity import SeverityRating, SeverityLevel


@dataclass
class GapSummary:
    """Summary of gaps for a jurisdiction pair."""
    
    jurisdiction_a: str
    jurisdiction_b: str
    total_gaps: int
    gaps_by_type: dict[str, int]
    high_severity_count: int
    requires_review_count: int
    top_gaps: list[dict]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'jurisdiction_a': self.jurisdiction_a,
            'jurisdiction_b': self.jurisdiction_b,
            'total_gaps': self.total_gaps,
            'gaps_by_type': self.gaps_by_type,
            'high_severity_count': self.high_severity_count,
            'requires_review_count': self.requires_review_count,
            'top_gaps': self.top_gaps
        }


@dataclass
class ComplianceReport:
    """Comprehensive compliance analysis report."""
    
    report_id: str
    generated_at: datetime
    jurisdictions_analyzed: list[str]
    document_count: int
    clause_count: int
    gap_summaries: list[GapSummary]
    ambiguity_reports: list[dict]
    enforcement_scenarios: list[dict]
    severity_summary: dict
    recommendations: list[str]
    disclaimers: list[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'jurisdictions_analyzed': self.jurisdictions_analyzed,
            'document_count': self.document_count,
            'clause_count': self.clause_count,
            'gap_summaries': [g.to_dict() for g in self.gap_summaries],
            'ambiguity_reports': self.ambiguity_reports,
            'enforcement_scenarios': self.enforcement_scenarios,
            'severity_summary': self.severity_summary,
            'recommendations': self.recommendations,
            'disclaimers': self.disclaimers
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class ReportGenerator:
    """
    Generates reports from regulatory gap analysis.
    
    Reports emphasize uncertainty and the need for legal review.
    No prescriptive recommendations are made.
    """
    
    STANDARD_DISCLAIMERS = [
        "This report is for informational purposes only and does not constitute legal advice.",
        "All findings require review by qualified legal counsel before any compliance decisions.",
        "Risk assessments are based on conservative modeling and may not reflect actual enforcement outcomes.",
        "This analysis may not capture all relevant regulatory requirements or recent changes.",
        "The tool's interpretations should not be relied upon as authoritative regulatory guidance.",
    ]
    
    def __init__(self, report_prefix: str = "REG-GAP"):
        """Initialize report generator."""
        self.report_prefix = report_prefix
        self._report_counter = 0
    
    def generate_gap_summary(
        self,
        gaps: list[JurisdictionalGap],
        jurisdiction_a: str,
        jurisdiction_b: str,
        top_n: int = 5
    ) -> GapSummary:
        """
        Generate summary for gaps between two jurisdictions.
        
        Args:
            gaps: List of identified gaps
            jurisdiction_a: First jurisdiction
            jurisdiction_b: Second jurisdiction
            top_n: Number of top gaps to include in detail
            
        Returns:
            GapSummary with aggregated statistics
        """
        # Count by type
        by_type: dict[str, int] = {}
        for gap in gaps:
            type_name = gap.gap_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        # Count high severity and review required
        high_severity = sum(1 for g in gaps if g.severity >= 0.7)
        requires_review = sum(1 for g in gaps if g.requires_legal_review)
        
        # Get top gaps by severity
        sorted_gaps = sorted(gaps, key=lambda g: g.severity, reverse=True)
        top_gaps = [
            {
                'type': g.gap_type.value,
                'description': g.description,
                'severity': g.severity,
                'recommendations': g.recommendations[:2]  # Limit recommendations
            }
            for g in sorted_gaps[:top_n]
        ]
        
        return GapSummary(
            jurisdiction_a=jurisdiction_a,
            jurisdiction_b=jurisdiction_b,
            total_gaps=len(gaps),
            gaps_by_type=by_type,
            high_severity_count=high_severity,
            requires_review_count=requires_review,
            top_gaps=top_gaps
        )
    
    def generate_compliance_report(
        self,
        jurisdictions: list[str],
        gap_matrix: dict[tuple[str, str], list[JurisdictionalGap]],
        ambiguity_reports: list[AmbiguityReport],
        enforcement_scenarios: list[EnforcementScenario],
        severity_ratings: list[SeverityRating],
        document_count: int = 0,
        clause_count: int = 0
    ) -> ComplianceReport:
        """
        Generate comprehensive compliance report.
        
        Args:
            jurisdictions: List of analyzed jurisdictions
            gap_matrix: Matrix of gaps between jurisdiction pairs
            ambiguity_reports: List of ambiguity analysis reports
            enforcement_scenarios: List of enforcement scenarios
            severity_ratings: List of severity ratings
            document_count: Number of documents analyzed
            clause_count: Number of clauses extracted
            
        Returns:
            ComplianceReport with full analysis
        """
        self._report_counter += 1
        report_id = f"{self.report_prefix}-{self._report_counter:05d}"
        
        # Generate gap summaries
        gap_summaries = []
        for (j_a, j_b), gaps in gap_matrix.items():
            summary = self.generate_gap_summary(gaps, j_a, j_b)
            gap_summaries.append(summary)
        
        # Process ambiguity reports
        amb_data = [
            {
                'document_id': ar.document_id,
                'jurisdiction': ar.jurisdiction,
                'total_instances': ar.total_instances,
                'ambiguity_score': ar.ambiguity_score,
                'high_severity_count': ar.high_severity_count
            }
            for ar in ambiguity_reports
        ]
        
        # Process enforcement scenarios
        enf_data = [
            {
                'scenario_id': es.scenario_id,
                'description': es.description,
                'likelihood': es.likelihood.name,
                'severity_score': es.severity_score,
                'requires_legal_review': es.requires_legal_review
            }
            for es in enforcement_scenarios
        ]
        
        # Generate severity summary
        severity_summary = self._summarize_severity(severity_ratings)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            gap_summaries, ambiguity_reports, enforcement_scenarios
        )
        
        return ComplianceReport(
            report_id=report_id,
            generated_at=datetime.now(),
            jurisdictions_analyzed=jurisdictions,
            document_count=document_count,
            clause_count=clause_count,
            gap_summaries=gap_summaries,
            ambiguity_reports=amb_data,
            enforcement_scenarios=enf_data,
            severity_summary=severity_summary,
            recommendations=recommendations,
            disclaimers=self.STANDARD_DISCLAIMERS
        )
    
    def _summarize_severity(self, ratings: list[SeverityRating]) -> dict:
        """Summarize severity ratings."""
        if not ratings:
            return {'message': 'No severity ratings available'}
        
        counts = {level.name: 0 for level in SeverityLevel}
        for rating in ratings:
            counts[rating.level.name] += 1
        
        total = len(ratings)
        avg_score = sum(r.score for r in ratings) / total
        
        return {
            'total_rated': total,
            'counts_by_level': counts,
            'average_score': round(avg_score, 3),
            'critical_count': counts['CRITICAL'],
            'high_count': counts['HIGH'],
            'requires_immediate_attention': sum(
                1 for r in ratings if r.requires_immediate_attention
            ),
            'requires_legal_review': sum(
                1 for r in ratings if r.requires_legal_review
            )
        }
    
    def _generate_recommendations(
        self,
        gap_summaries: list[GapSummary],
        ambiguity_reports: list[AmbiguityReport],
        enforcement_scenarios: list[EnforcementScenario]
    ) -> list[str]:
        """Generate high-level recommendations (non-prescriptive)."""
        recommendations = []
        
        # Always start with legal review recommendation
        recommendations.append(
            "PRIORITY: Engage qualified legal counsel to review all high-severity findings"
        )
        
        # Gap-based recommendations
        total_high_severity = sum(g.high_severity_count for g in gap_summaries)
        if total_high_severity > 0:
            recommendations.append(
                f"GAPS: {total_high_severity} high-severity jurisdictional gaps identified - "
                "prioritize legal review of cross-border compliance"
            )
        
        # Ambiguity-based recommendations
        total_ambiguity = sum(ar.high_severity_count for ar in ambiguity_reports)
        if total_ambiguity > 5:
            recommendations.append(
                f"AMBIGUITY: {total_ambiguity} high-severity ambiguities detected - "
                "document interpretation rationale for all ambiguous terms"
            )
        
        # Enforcement-based recommendations
        high_risk_scenarios = [
            es for es in enforcement_scenarios if es.severity_score >= 0.7
        ]
        if high_risk_scenarios:
            recommendations.append(
                f"ENFORCEMENT: {len(high_risk_scenarios)} high-risk enforcement scenarios modeled - "
                "review and strengthen compliance controls"
            )
        
        # General recommendation
        recommendations.append(
            "DOCUMENTATION: Maintain records of compliance interpretation decisions and rationale"
        )
        
        return recommendations
    
    def generate_markdown_report(self, report: ComplianceReport) -> str:
        """
        Generate a markdown-formatted report.
        
        Args:
            report: ComplianceReport to format
            
        Returns:
            Markdown string
        """
        lines = []
        
        # Header
        lines.append(f"# Regulatory Gap Analysis Report")
        lines.append(f"**Report ID:** {report.report_id}")
        lines.append(f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Disclaimers
        lines.append("## ⚠️ Important Disclaimers")
        for disclaimer in report.disclaimers:
            lines.append(f"- {disclaimer}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append(f"- **Jurisdictions Analyzed:** {', '.join(report.jurisdictions_analyzed)}")
        lines.append(f"- **Documents Analyzed:** {report.document_count}")
        lines.append(f"- **Clauses Extracted:** {report.clause_count}")
        lines.append(f"- **Total Gaps Identified:** {sum(g.total_gaps for g in report.gap_summaries)}")
        lines.append("")
        
        # Severity Summary
        lines.append("## Severity Summary")
        ss = report.severity_summary
        if 'message' not in ss:
            lines.append(f"- **Critical Issues:** {ss.get('critical_count', 0)}")
            lines.append(f"- **High Priority Issues:** {ss.get('high_count', 0)}")
            lines.append(f"- **Requires Immediate Attention:** {ss.get('requires_immediate_attention', 0)}")
            lines.append(f"- **Requires Legal Review:** {ss.get('requires_legal_review', 0)}")
        lines.append("")
        
        # Gap Summaries
        lines.append("## Jurisdictional Gap Analysis")
        for gs in report.gap_summaries:
            lines.append(f"### {gs.jurisdiction_a} ↔ {gs.jurisdiction_b}")
            lines.append(f"- Total Gaps: {gs.total_gaps}")
            lines.append(f"- High Severity: {gs.high_severity_count}")
            lines.append(f"- Requires Review: {gs.requires_review_count}")
            if gs.top_gaps:
                lines.append("#### Top Issues")
                for gap in gs.top_gaps:
                    lines.append(f"- **{gap['type']}** (Severity: {gap['severity']:.2f})")
                    lines.append(f"  - {gap['description']}")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        lines.append("*Note: These are areas for review, not prescriptive actions.*")
        lines.append("")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("*This report was generated by RegulatoryGapAnalyzer. "
                     "It does not constitute legal advice.*")
        
        return "\n".join(lines)
    
    def generate_needs_review_list(
        self,
        gaps: list[JurisdictionalGap],
        ambiguities: list[AmbiguityInstance],
        scenarios: list[EnforcementScenario]
    ) -> list[dict]:
        """
        Generate a list of items flagged for legal review.
        
        Args:
            gaps: Jurisdictional gaps
            ambiguities: Ambiguity instances
            scenarios: Enforcement scenarios
            
        Returns:
            List of items requiring review
        """
        items = []
        
        # Gaps requiring review
        for gap in gaps:
            if gap.requires_legal_review:
                items.append({
                    'type': 'jurisdictional_gap',
                    'category': gap.gap_type.value,
                    'description': gap.description,
                    'severity': gap.severity,
                    'jurisdictions': [gap.jurisdiction_a, gap.jurisdiction_b],
                    'priority': 'HIGH' if gap.severity >= 0.7 else 'MEDIUM'
                })
        
        # High-severity ambiguities
        for amb in ambiguities:
            if amb.severity >= 0.6:
                items.append({
                    'type': 'ambiguity',
                    'category': amb.ambiguity_type.value,
                    'description': amb.trigger_phrase,
                    'context': amb.context[:100] + '...' if len(amb.context) > 100 else amb.context,
                    'severity': amb.severity,
                    'priority': 'HIGH' if amb.severity >= 0.7 else 'MEDIUM'
                })
        
        # Enforcement scenarios
        for scenario in scenarios:
            if scenario.requires_legal_review:
                items.append({
                    'type': 'enforcement_scenario',
                    'category': scenario.scenario_id,
                    'description': scenario.description,
                    'severity': scenario.severity_score,
                    'likelihood': scenario.likelihood.name,
                    'priority': 'HIGH' if scenario.severity_score >= 0.7 else 'MEDIUM'
                })
        
        # Sort by priority and severity
        items.sort(key=lambda x: (-1 if x['priority'] == 'HIGH' else 0, -x['severity']))
        
        return items
