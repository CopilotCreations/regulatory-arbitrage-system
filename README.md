# RegulatoryGapAnalyzer

A compliance research tool designed to identify regulatory ambiguity, divergence, and escalation risk across jurisdictions. This tool analyzes gaps to **REDUCE risk**, not exploit it.

## ⚠️ Important Disclaimer

**This tool does not provide legal advice.** All analysis results require review by qualified legal counsel before any compliance decisions are made. The tool's outputs emphasize uncertainty and the need for professional review.

## Features

- **Document Ingestion**: Load regulatory texts from PDF, HTML, DOCX, and plain text formats
- **Clause Extraction**: Identify obligations, prohibitions, permissions, and conditions
- **Definition Extraction**: Extract and cross-reference defined terms
- **Ambiguity Detection**: Flag vague standards, unclear thresholds, and undefined terms
- **Jurisdictional Comparison**: Compare regulations across different jurisdictions
- **Risk Modeling**: Conservative enforcement modeling assuming worst-case interpretation
- **Gap Reporting**: Generate heatmaps, rankings, and "needs legal review" flags

## Installation

```bash
# Basic installation
pip install -e .

# With all document format support
pip install -e ".[all]"

# With development dependencies
pip install -e ".[dev]"
```

## Quick Start

### Run the Demo

```bash
python -m reg_gap.cli demo
```

### Analyze a Document

```bash
python -m reg_gap.cli analyze document.pdf --jurisdiction US-SEC
```

### Compare Documents

```bash
python -m reg_gap.cli compare us_regs.pdf eu_regs.pdf --jurisdictions US-SEC EU-MiFID
```

### Generate Full Report

```bash
python -m reg_gap.cli report doc1.pdf doc2.pdf --jurisdictions US-SEC EU-MiFID --output report.md
```

## Project Structure

```
reg_gap/
├── ingestion/
│   ├── loaders.py        # PDF, HTML, DOCX loaders
│   └── normalizer.py     # Text normalization
├── parsing/
│   ├── clause_extractor.py    # Extract obligations, prohibitions
│   ├── entity_recognizer.py   # Recognize regulatory entities
│   └── definitions.py         # Definition extraction
├── comparison/
│   ├── semantic_diff.py       # Semantic clause comparison
│   ├── jurisdictional.py      # Cross-jurisdiction analysis
│   └── ambiguity.py           # Ambiguity detection
├── risk/
│   ├── enforcement_model.py   # Conservative enforcement modeling
│   ├── severity.py            # Severity assessment
│   └── confidence_bounds.py   # Uncertainty quantification
├── reports/
│   ├── summaries.py          # Report generation
│   └── visualizations.py     # Heatmaps and rankings
├── cli.py                    # Command-line interface
└── tests/                    # Test suite
```

## Key Design Principles

### 1. Conservative Risk Modeling

The tool assumes **maximum plausible interpretation** by regulators:
- Ambiguous language is interpreted strictly
- Unclear thresholds are set at most stringent levels
- Timing requirements are interpreted as requiring immediate action

### 2. No Prescriptive Recommendations

The tool explicitly avoids:
- ❌ Automated policy recommendations
- ❌ Execution logic
- ❌ Suggesting how to exploit gaps

Instead, it provides:
- ✅ "Needs legal review" flags
- ✅ Uncertainty quantification
- ✅ Identification of potential issues

### 3. Emphasis on Uncertainty

All outputs include:
- Confidence bounds on risk estimates
- Explicit uncertainty levels
- Mandatory disclaimers about legal review

## Clause Classification

The tool classifies regulatory clauses as:

| Type | Indicators | Example |
|------|------------|---------|
| **Obligation** | shall, must, required | "The registrant shall file..." |
| **Prohibition** | shall not, prohibited | "No person may engage in..." |
| **Permission** | may, can, permitted | "The Commission may grant..." |
| **Condition** | if, when, unless | "If the threshold is exceeded..." |

## Difference Classification

When comparing jurisdictions, differences are classified as:

- **Stricter**: First jurisdiction has more restrictive requirements
- **Looser**: First jurisdiction has less restrictive requirements
- **Ambiguous**: Unclear which is more restrictive
- **Conflicting**: Direct contradiction between requirements

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=reg_gap

# Run specific test file
pytest reg_gap/tests/test_clause_extractor.py
```

## Safety & Ethics

This tool is designed to **make regulatory arbitrage harder** by:

1. Surfacing risks before exploitation becomes possible
2. Flagging gaps that require legal attention
3. Emphasizing conservative interpretations
4. Never providing "loopholes" or exploitation strategies

All outputs are designed for compliance officers and legal teams, not for circumventing regulations.

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please ensure all changes:

1. Maintain the safety-first design philosophy
2. Include appropriate tests
3. Do not add prescriptive recommendation logic
4. Include proper uncertainty quantification
