# Flyber Python Source

This directory contains the Python source used to analyze the Flyber datasets and generate the principal project artifacts.

## Scripts

1. `scripts/01_analyze_flyber.py`
   - Reads the supplied Section 3 and Section 5 workbooks.
   - Parses raw Office Open XML worksheet data.
   - Aggregates daily event, device, page, and location counts.
   - Writes `flyber_analysis.json`.

2. `scripts/02_create_visualizations.py`
   - Reads the generated analysis JSON.
   - Calculates monthly growth, campaign averages, peaks, and event-type growth multiples.
   - Generates four PNG visualizations.
   - Writes `flyber_metrics.json`.

3. `scripts/03_build_section3_workbook.py`
   - Reopens the untouched Section 3 template.
   - Preserves the raw event-log worksheet.
   - Populates and formats the existing `ETL` worksheet.
   - Adds reconciliation controls and workbook compatibility settings.

4. `scripts/04_populate_proposal.py`
   - Populates the supplied Word proposal template.
   - Inserts stakeholder, modeling, ETL, visualization, analysis, and warehouse content.
   - Embeds the generated charts.

## Expected Project Layout

Run the source from the project root with the supplied files in `upload/`:

```text
project-root/
|-- upload/
|   |-- section-3-event-logs-template.xlsx
|   |-- section-5-data.xlsx
|   `-- template-of-flyber-data-strategy-mvp.docx
|-- outputs/
|   `-- flyber/
`-- python-source/
    |-- README.md
    |-- requirements.txt
    |-- run_pipeline.py
    `-- scripts/
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r python-source/requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Execution

```bash
python python-source/run_pipeline.py
```

The scripts use relative project paths so that the original templates remain separate from generated files. The pipeline should be executed from a copy of the project directory rather than against the only copy of the source data.

## Validation

The generated Section 3 workbook should satisfy the following checks:

- Raw worksheet: 124,980 data rows plus one header row.
- ETL worksheet: daily summaries for October 5-11, 2019.
- Numeric count format: `#,##0`.
- Event-type, device-type, page-type, and location reconciliations: `PASS`.
