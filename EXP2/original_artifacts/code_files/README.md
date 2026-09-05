# Experiment 2 

 runtime path:

`requirement → common template pool → semantic template selector → probe generation → Judges 1–2
→ normalization/compilation/validation → Judge 3 → solver execution → one probe-aware witness
verifier → root-cause adjudicator → classification/localization`

Judges 1–3 use only `ACCEPT` or `REPAIR`. Judge 3 compares the original requirement, generated
claim, and exact final normalized executable probe; it is not a second witness verifier.
Dual-witness consensus, alternate verifier policies, Track 0/A/A+, fallback classifiers,
metamorphic machinery, query-shadow machinery, and old experimental runs are not active or
included.


## Probe-generator visibility

Every probe-generation attempt receives:

- the full problem description/narrative;
- the approved target requirement text and original category;
- relevant problem data;
- requirement metadata;
- the candidate model slice;
- repair context when applicable.

For semantic lower/upper bounds, a weaker declared variable bound is not itself a violation. The
runtime searches the full candidate feasible region and reports FAIL only if it finds a feasible
violating point; no such witness produces PASS.

## Verification and diagnosis

There is one witness verifier: Its only
semantic decisions are `YES` and `NO`. `YES` retains FAIL; `NO` produces `WITNESS_V_REJECT`, which
is unresolved and never PASS. Missing evidence or a technical verifier failure produces
`UNRESOLVED` without a semantic decision.

Final runtime verdicts are only `correct`, `incorrect`, or `pipeline_error`.
Requirement-local failures are `UNRESOLVED`; the result records `unresolved_requirement_count` and
`evaluation_complete`. `pipeline_error` is reserved for a genuine system-level failure that
prevents meaningful candidate evaluation.

**SILENT EXACT LOCALIZATION** is offline diagnosis/scoring only and is not imported into runtime
routing, probe generation, verification, or verdict construction.

## Validation status

Static compilation, unit tests, prompt-freeze checks, category equality, changelog application,
catalog cleanup, and protected-asset hashes are validated before packaging. No experiment and no
end-to-end Gurobi execution were run during this work.

See `REPRODUCE.md` and the files under `reports/` for exact audit records.
