# SilentOR

SilentOR converts each  requirement into an mathematical executable, solver-backed probe. The retained source supplies the full semantic template pool to the selector, validates and normalizes the chosen probe, executes it against the candidate model, and reviews any witness before root-cause localization.

```text
for each candidate model:
    load its problem description and approved requirement list
    for each requirement:
        select a probe template from the common semantic pool
        generate a typed probe from the requirement and visible metadata
        obtain ACCEPT or REPAIR from judges 1 and 2
        normalize and compile the executable probe
        obtain ACCEPT or REPAIR from judge 3 on claim–probe equivalence
        execute the accepted probe with Gurobi
        if a counterexample is found:
            ask the probe-aware witness verifier whether it proves a violation
    adjudicate the root requirement among confirmed violations
    emit the candidate verdict and diagnosis records
```

The witness verifier and root-cause adjudicator are documented in [the exact source](../configs_prompts/source/shadow_witness_architecture.py). Exact localization is a diagnosis/scoring metric and does not feed candidate verdicts or probe selection.

## Result scope

The Gemma SilentOR output records 95 of 111 candidates; 90 are valid for the reported probe-aware-root policy scores. Gemma SilentOR is therefore incomplete.
