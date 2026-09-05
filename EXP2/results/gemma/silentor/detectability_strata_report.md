# Mutant detectability strata

`LEGACY_ALL` preserves direct comparability with earlier Exp-2 results. `PRIMARY_BEHAVIORAL` excludes structural-only, domain-equivalent, and numerically ambiguous perturbations. Certified continuous-sliver witnesses remain behaviorally detectable.

- gemma3:12b / B / BEHAVIORALLY_DETECTABLE: detection 8/15; PEL 2/15 (13.33%)
- gemma3:12b / B / LEGACY_ALL: detection 34/62; PEL 16/62 (25.81%)
- gemma3:12b / B / PRIMARY_BEHAVIORAL: detection 34/62; PEL 16/62 (25.81%)
- gemma3:12b / B / STANDARD: detection 26/47; PEL 14/47 (29.79%)
