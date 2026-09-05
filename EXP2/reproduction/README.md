# Reproduction

## Exact runtime snapshot

The cleanest way to reproduce the supplied implementation is to extract [EXP2_code_snapshot.zip](../original_artifacts/code/EXP2_code_snapshot.zip) into a fresh directory and follow its exact [REPRODUCE.md](../original_artifacts/code_files/REPRODUCE.md).

The run requires Python dependencies from `requirements.txt`, an available Gurobi installation and license, and the configured language-model provider (the supplied runs use Ollama model names recorded in their CSV/JSON metadata). Run static checks separately from solver-backed execution; passing unit or manifest checks is not an end-to-end Gurobi result.

## Inspecting the published results

1. Start with [results/STATUS.md](../results/STATUS.md).
2. Use [results/summary_metrics.csv](../results/summary_metrics.csv) for the compact comparison.
3. Use the exact Direct Detector and Requirement List `results.csv` files under `results/`.
4. Extract the exact SilentOR run ZIPs under `original_artifacts/runs/` when raw candidate traces or the full large `results.csv` files are needed.

This documentation build does not rerun any experiment or alter any result row.
