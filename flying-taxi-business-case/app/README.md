# Flyber MVP Launch Analysis Source

Run the full reproducible pipeline from the project workspace:

```bash
python flyber-analysis-source/run_pipeline.py
```

Alternatively, call `flyber_analysis.py` directly with `--taxi`, `--survey`,
and `--output-dir`. Add `--write-tableau` to emit the full enriched CSV used
for Tableau Public.

The program analyzes all taxi records, preserves raw descriptive statistics,
and separately applies the following operational-quality criteria for launch
decisions: 60-7,200 seconds, 0.25-50 miles, 1-6 passengers, 1-80 mph average
speed, chronologically valid timestamps, and plausible NYC-metro coordinate
bounds. It records every exclusion in `data_quality_reconciliation.csv`.

The fare is a historical 2016 TLC proxy, not an observed fare. The program uses
an official NYC Open Data NTA GeoJSON as a third-party spatial overlay and
records the 2016/2020 boundary-year mismatch as a limitation.

Run the independent package checks after building the deck. The `--pptx` path
is a local editable presentation input; editable Office files are deliberately
not included in this repository.

```bash
python flyber-analysis-source/validate_deliverables.py \
  --taxi upload/taxi_rides.csv \
  --survey upload/user-research.csv \
  --output-dir flyber-analysis-output \
  --pptx /path/to/local-presentation.pptx \
  --report deliverables/validation-results.json
```
