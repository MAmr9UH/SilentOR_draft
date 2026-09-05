# Dual-verifier shadow policy comparison

Gold labels are introduced only by `score_exp2.py`. Neither live verifier nor the root-cause adjudicator receives mutation labels or expected answers.

Valid Track B rows scored: 90. Invalid rows excluded: 5 (see `shadow_policy_invalid_rows.csv`).

## official_raw_current

Official raw FAILs + current deterministic ranking

- Base false positives: 7/28 (0.25)
- Mutant detection: 34/62 (0.5484)
- Primary Exact Localization: 16/62 (25.81%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.289
- True mutated-requirement witness retention: 40/40 (1.0)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## blind_current

Blind false-witness verifier + current deterministic ranking

- Base false positives: 7/28 (0.25)
- Mutant detection: 35/62 (0.5645)
- Primary Exact Localization: 14/62 (22.58%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.2729
- True mutated-requirement witness retention: 24/40 (0.6)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## blind_root

Blind false-witness verifier + Root-Cause Adjudicator

- Base false positives: 7/28 (0.25)
- Mutant detection: 35/62 (0.5645)
- Primary Exact Localization: 15/62 (24.19%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.2842
- True mutated-requirement witness retention: 24/40 (0.6)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## blind_hybrid

Blind verifier + adjudicator with flagged deterministic fallback

- Base false positives: 7/28 (0.25)
- Mutant detection: 35/62 (0.5645)
- Primary Exact Localization: 15/62 (24.19%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.2842
- True mutated-requirement witness retention: 24/40 (0.6)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## probe_aware_current

Probe-aware OR verifier + current deterministic ranking

- Base false positives: 14/28 (0.5)
- Mutant detection: 48/62 (0.7742)
- Primary Exact Localization: 21/62 (33.87%)
- Top-2 localization: 27/62 (43.55%)
- Top-3 localization: 29/62 (46.77%)
- Mean reciprocal rank: 0.4154
- True mutated-requirement witness retention: 37/40 (0.925)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## probe_aware_root

Probe-aware OR verifier + Root-Cause Adjudicator

- Base false positives: 14/28 (0.5)
- Mutant detection: 48/62 (0.7742)
- Primary Exact Localization: 21/62 (33.87%)
- Top-2 localization: 27/62 (43.55%)
- Top-3 localization: 29/62 (46.77%)
- Mean reciprocal rank: 0.417
- True mutated-requirement witness retention: 37/40 (0.925)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## probe_aware_hybrid

Probe-aware verifier + adjudicator with flagged deterministic fallback

- Base false positives: 14/28 (0.5)
- Mutant detection: 48/62 (0.7742)
- Primary Exact Localization: 21/62 (33.87%)
- Top-2 localization: 27/62 (43.55%)
- Top-3 localization: 29/62 (46.77%)
- Mean reciprocal rank: 0.417
- True mutated-requirement witness retention: 37/40 (0.925)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## dual_current

Dual YES/YES consensus + current deterministic ranking

- Base false positives: 7/28 (0.25)
- Mutant detection: 34/62 (0.5484)
- Primary Exact Localization: 16/62 (25.81%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.289
- True mutated-requirement witness retention: 24/40 (0.6)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## dual_root

Dual YES/YES consensus + Root-Cause Adjudicator

- Base false positives: 7/28 (0.25)
- Mutant detection: 34/62 (0.5484)
- Primary Exact Localization: 16/62 (25.81%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.2923
- True mutated-requirement witness retention: 24/40 (0.6)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

## dual_hybrid

Dual consensus + adjudicator with flagged deterministic fallback

- Base false positives: 7/28 (0.25)
- Mutant detection: 34/62 (0.5484)
- Primary Exact Localization: 16/62 (25.81%)
- Top-2 localization: 19/62 (30.65%)
- Top-3 localization: 19/62 (30.65%)
- Mean reciprocal rank: 0.2923
- True mutated-requirement witness retention: 24/40 (0.6)
- Dual decisive-agreement rate: 0.2639
- Dual unconfirmed rate: 0.3414

