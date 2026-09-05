# SilentOR probe templates

The exact implementation and generator guidance are in [probe_engine.py](../configs_prompts/source/probe_engine.py). The retained code supplies the same ordered semantic template pool to every requirement; selection is based on mathematical structure.

## `linear_requirement_probe`

Searches the candidate feasible region for a violation of one linear comparison, ratio, or balance.
## `implication_probe`

Searches for a feasible assignment where an antecedent holds and the required consequent fails.
## `check_variable_property`

Checks one named variable property: existence, type, lower bound, or upper bound.
## `maximize_linear_violation`

Maximizes one or more explicit linear violation expressions; equality needs both directions.
## `constraint_row_probe`

Inspects one named row's terms, sense, and right-hand side; mismatches are warning-only because equivalent formulations may exist.
## `indexed_constraint_family_probe`

Checks every authoritative member of an indexed family and searches each member for a violation.
## `check_constraint_exists_by_terms`

Performs a weak structural presence check; absence is warning-only.
## `objective_difference_probe`

Compares the candidate objective with the required objective over the full candidate feasible region.
## `check_objective_terms`

Provides diagnostic-only objective-term inspection; it is not the verdict-bearing objective check.

Pipeline-owned tolerances and normalization rules remain in source code. This page is explanatory and is not an executable specification.
