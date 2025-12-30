"""
Visualization generation for regulatory gap analysis.

Creates heatmaps, rankings, and other visual representations
of regulatory gaps and risks.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Any

from ..comparison.jurisdictional import JurisdictionalGap, GapType
from ..comparison.ambiguity import AmbiguityInstance, AmbiguityType
from ..risk.severity import SeverityLevel


@dataclass
class HeatmapData:
    """Data structure for heatmap visualization."""
    
    rows: list[str]  # e.g., jurisdictions
    columns: list[str]  # e.g., gap types or other jurisdictions
    values: list[list[float]]  # 2D matrix of values
    title: str = "Regulatory Gap Heatmap"
    value_label: str = "Severity"
    min_value: float = 0.0
    max_value: float = 1.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'rows': self.rows,
            'columns': self.columns,
            'values': self.values,
            'title': self.title,
            'value_label': self.value_label,
            'min_value': self.min_value,
            'max_value': self.max_value
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class RankingData:
    """Data structure for ranking visualization."""
    
    items: list[dict]  # List of {name, value, category, ...}
    title: str = "Ranking"
    value_label: str = "Score"
    ascending: bool = False  # False = highest first
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'items': self.items,
            'title': self.title,
            'value_label': self.value_label,
            'ascending': self.ascending
        }


class Visualizer:
    """
    Generates visualization data for regulatory gap analysis.
    
    Outputs structured data that can be rendered by various
    visualization libraries (matplotlib, plotly, etc.)
    """
    
    # Color scales for severity
    SEVERITY_COLORS = {
        'critical': '#d32f2f',    # Red
        'high': '#f57c00',        # Orange
        'medium': '#fbc02d',      # Yellow
        'low': '#388e3c',         # Green
        'informational': '#1976d2' # Blue
    }
    
    def generate_jurisdiction_heatmap(
        self,
        gap_matrix: dict[tuple[str, str], list[JurisdictionalGap]]
    ) -> HeatmapData:
        """
        Generate heatmap of gaps between jurisdictions.
        
        Args:
            gap_matrix: Matrix of gaps between jurisdiction pairs
            
        Returns:
            HeatmapData for visualization
        """
        # Extract unique jurisdictions
        jurisdictions = set()
        for (j_a, j_b) in gap_matrix.keys():
            jurisdictions.add(j_a)
            jurisdictions.add(j_b)
        
        jurisdictions = sorted(jurisdictions)
        n = len(jurisdictions)
        
        # Build severity matrix
        values = [[0.0 for _ in range(n)] for _ in range(n)]
        
        for (j_a, j_b), gaps in gap_matrix.items():
            i = jurisdictions.index(j_a)
            j = jurisdictions.index(j_b)
            
            if gaps:
                avg_severity = sum(g.severity for g in gaps) / len(gaps)
            else:
                avg_severity = 0.0
            
            values[i][j] = avg_severity
            values[j][i] = avg_severity  # Symmetric
        
        return HeatmapData(
            rows=jurisdictions,
            columns=jurisdictions,
            values=values,
            title="Jurisdictional Gap Severity Heatmap",
            value_label="Average Gap Severity",
            min_value=0.0,
            max_value=1.0
        )
    
    def generate_gap_type_heatmap(
        self,
        gap_matrix: dict[tuple[str, str], list[JurisdictionalGap]]
    ) -> HeatmapData:
        """
        Generate heatmap of gap types by jurisdiction pair.
        
        Args:
            gap_matrix: Matrix of gaps between jurisdiction pairs
            
        Returns:
            HeatmapData for visualization
        """
        # Get all gap types
        gap_types = [gt.value for gt in GapType]
        
        # Get all jurisdiction pairs
        pairs = [f"{j_a} vs {j_b}" for (j_a, j_b) in gap_matrix.keys()]
        
        if not pairs:
            return HeatmapData(
                rows=[],
                columns=gap_types,
                values=[],
                title="Gap Types by Jurisdiction Pair"
            )
        
        # Count gaps by type for each pair
        values = []
        for (j_a, j_b), gaps in gap_matrix.items():
            row = []
            for gt in GapType:
                count = sum(1 for g in gaps if g.gap_type == gt)
                row.append(float(count))
            values.append(row)
        
        return HeatmapData(
            rows=pairs,
            columns=gap_types,
            values=values,
            title="Gap Types by Jurisdiction Pair",
            value_label="Gap Count",
            min_value=0.0,
            max_value=max(max(row) for row in values) if values else 1.0
        )
    
    def generate_ambiguity_ranking(
        self,
        ambiguities: list[AmbiguityInstance],
        top_n: int = 20
    ) -> RankingData:
        """
        Generate ranking of ambiguities by severity.
        
        Args:
            ambiguities: List of ambiguity instances
            top_n: Number of top items to include
            
        Returns:
            RankingData for visualization
        """
        # Sort by severity
        sorted_amb = sorted(ambiguities, key=lambda a: a.severity, reverse=True)[:top_n]
        
        items = [
            {
                'name': amb.trigger_phrase[:50] + ('...' if len(amb.trigger_phrase) > 50 else ''),
                'value': amb.severity,
                'category': amb.ambiguity_type.value,
                'confidence': amb.confidence,
                'context': amb.context[:100] if amb.context else ''
            }
            for amb in sorted_amb
        ]
        
        return RankingData(
            items=items,
            title="Top Ambiguities by Severity",
            value_label="Severity Score",
            ascending=False
        )
    
    def generate_severity_distribution(
        self,
        severities: list[float]
    ) -> dict:
        """
        Generate distribution data for severity scores.
        
        Args:
            severities: List of severity scores
            
        Returns:
            Distribution data for visualization
        """
        if not severities:
            return {
                'bins': [],
                'counts': [],
                'title': 'Severity Distribution',
                'total': 0
            }
        
        # Create bins
        bins = [
            (0.0, 0.2, 'Informational'),
            (0.2, 0.4, 'Low'),
            (0.4, 0.6, 'Medium'),
            (0.6, 0.8, 'High'),
            (0.8, 1.0, 'Critical')
        ]
        
        counts = []
        labels = []
        
        for low, high, label in bins:
            count = sum(1 for s in severities if low <= s < high)
            counts.append(count)
            labels.append(label)
        
        # Handle exactly 1.0
        counts[-1] += sum(1 for s in severities if s == 1.0)
        
        return {
            'labels': labels,
            'counts': counts,
            'title': 'Severity Distribution',
            'total': len(severities),
            'mean': sum(severities) / len(severities),
            'max': max(severities),
            'min': min(severities)
        }
    
    def generate_gap_summary_chart(
        self,
        gap_matrix: dict[tuple[str, str], list[JurisdictionalGap]]
    ) -> dict:
        """
        Generate summary chart data for gaps.
        
        Args:
            gap_matrix: Matrix of gaps between jurisdiction pairs
            
        Returns:
            Chart data for visualization
        """
        # Count by gap type across all pairs
        type_counts = {gt.value: 0 for gt in GapType}
        severity_by_type = {gt.value: [] for gt in GapType}
        
        for gaps in gap_matrix.values():
            for gap in gaps:
                type_counts[gap.gap_type.value] += 1
                severity_by_type[gap.gap_type.value].append(gap.severity)
        
        # Calculate average severity by type
        avg_severity = {}
        for gt, severities in severity_by_type.items():
            if severities:
                avg_severity[gt] = sum(severities) / len(severities)
            else:
                avg_severity[gt] = 0.0
        
        return {
            'type_counts': type_counts,
            'average_severity_by_type': avg_severity,
            'total_gaps': sum(type_counts.values()),
            'title': 'Gap Analysis Summary'
        }
    
    def generate_review_priority_matrix(
        self,
        gaps: list[JurisdictionalGap],
        ambiguities: list[AmbiguityInstance]
    ) -> HeatmapData:
        """
        Generate priority matrix for items requiring review.
        
        Plots items by severity vs confidence to help prioritize
        legal review efforts.
        
        Args:
            gaps: Jurisdictional gaps
            ambiguities: Ambiguity instances
            
        Returns:
            HeatmapData representing priority matrix
        """
        # Define severity and confidence bins
        severity_bins = ['Low (0-0.33)', 'Medium (0.33-0.66)', 'High (0.66-1.0)']
        confidence_bins = ['Low Confidence', 'Medium Confidence', 'High Confidence']
        
        # Initialize counts
        values = [[0 for _ in range(3)] for _ in range(3)]
        
        # Helper to get bin index
        def get_bin(value: float) -> int:
            if value < 0.33:
                return 0
            elif value < 0.66:
                return 1
            else:
                return 2
        
        # Count gaps
        for gap in gaps:
            if gap.requires_legal_review:
                sev_idx = get_bin(gap.severity)
                conf_idx = get_bin(gap.confidence)
                values[sev_idx][conf_idx] += 1
        
        # Count ambiguities
        for amb in ambiguities:
            if amb.severity >= 0.5:
                sev_idx = get_bin(amb.severity)
                conf_idx = get_bin(amb.confidence)
                values[sev_idx][conf_idx] += 1
        
        return HeatmapData(
            rows=severity_bins,
            columns=confidence_bins,
            values=values,
            title="Review Priority Matrix",
            value_label="Items Requiring Review",
            min_value=0.0,
            max_value=float(max(max(row) for row in values)) if any(values) else 1.0
        )
    
    def generate_ascii_heatmap(self, heatmap: HeatmapData) -> str:
        """
        Generate ASCII representation of heatmap for terminal display.
        
        Args:
            heatmap: HeatmapData to visualize
            
        Returns:
            ASCII string representation
        """
        if not heatmap.rows or not heatmap.columns:
            return "No data to display"
        
        # Symbols for different severity levels
        symbols = [' ', '░', '▒', '▓', '█']
        
        def value_to_symbol(val: float) -> str:
            if heatmap.max_value == heatmap.min_value:
                return symbols[2]
            normalized = (val - heatmap.min_value) / (heatmap.max_value - heatmap.min_value)
            idx = min(4, int(normalized * 5))
            return symbols[idx]
        
        lines = []
        lines.append(f"\n{heatmap.title}")
        lines.append("=" * len(heatmap.title))
        
        # Header
        max_row_len = max(len(r) for r in heatmap.rows)
        header = " " * (max_row_len + 2)
        for col in heatmap.columns:
            header += col[:8].center(10)
        lines.append(header)
        
        # Rows
        for i, row_name in enumerate(heatmap.rows):
            row_str = row_name.ljust(max_row_len) + " │"
            for j, _ in enumerate(heatmap.columns):
                val = heatmap.values[i][j]
                sym = value_to_symbol(val)
                row_str += f"   {sym}{sym}{sym}    "
            lines.append(row_str)
        
        # Legend
        lines.append("")
        lines.append(f"Legend: {heatmap.value_label}")
        lines.append(f"  ' ' = {heatmap.min_value:.2f}  "
                    f"'░' = Low  '▒' = Med  '▓' = High  '█' = {heatmap.max_value:.2f}")
        
        return "\n".join(lines)
    
    def generate_ascii_ranking(self, ranking: RankingData, max_items: int = 10) -> str:
        """
        Generate ASCII representation of ranking for terminal display.
        
        Args:
            ranking: RankingData to visualize
            max_items: Maximum items to show
            
        Returns:
            ASCII string representation
        """
        if not ranking.items:
            return "No items to rank"
        
        lines = []
        lines.append(f"\n{ranking.title}")
        lines.append("=" * len(ranking.title))
        
        items = ranking.items[:max_items]
        max_val = max(item['value'] for item in items) if items else 1.0
        
        for i, item in enumerate(items, 1):
            name = item['name'][:40].ljust(40)
            val = item['value']
            bar_len = int((val / max_val) * 20) if max_val > 0 else 0
            bar = '█' * bar_len + '░' * (20 - bar_len)
            category = item.get('category', '')[:15].ljust(15)
            
            lines.append(f"{i:3}. {name} │{bar}│ {val:.3f} [{category}]")
        
        return "\n".join(lines)
