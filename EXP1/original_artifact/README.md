# SilentOR EXP1 — Reviewer Artifact

This package contains the final Experiment 1 evaluation tables and the exact core experiment assets needed to understand or rerun the evaluation. Development history, duplicate archives, temporary execution workdirs, partial runs, cache files, and operating-system metadata were intentionally excluded.

## Final result sets

Each model table contains 410 rows: 41 problems × 10 samples.

- `results/llama3_3_70b_results.csv`
- `results/gemma3_12b_results.csv`
- `results/gpt5_nano_results.csv`
- `results/sirl_gurobi_results.csv`

`results_summary.csv` gives a compact count summary across the four model result sets.

The reviewer-facing CSV copies omit only machine-local file-path columns and the internal prompt release tag; scientific labels, requirement failures, objective-match indicators, counts, timings, and model identifiers are preserved.

## Experiment assets

- `experiment/run_exp1.py` — EXP1 runner
- `experiment/Problems_main.json` — 41-problem benchmark specification
- `experiment/checkers.py` — output-level checker registry
- `experiment/checker_specs.json` — checker specification data
- `experiment/formulation_audit.py` — formulation-level audit logic
- `requirements.txt` — Python package dependencies

## Integrity

Use `SHA256SUMS.txt` to verify the packaged files.
