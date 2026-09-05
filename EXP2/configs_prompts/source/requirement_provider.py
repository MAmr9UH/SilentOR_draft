#!/usr/bin/env python3
"""
requirement_provider.py -- the single source of requirements for the V42 verifier, and the
prompt-safety boundary.

Two responsibilities:
  1. RequirementProvider(): returns the reviewed list from frozen_assets/Problems_main.json.

  2. build_candidate_prompt_payload(...): assembles EXACTLY what a verifier is allowed to see
     (problem description, requirement list, candidate code) and runs it through a hard
     sanitizer that strips/【refuses】 any leakage of:
        - the gold objective value
        - the injected_requirement_id / mutation identity
        - certification witnesses / audit internals / reference solutions
     If a forbidden token survives sanitization the function RAISES, so a leak fails loudly
     rather than silently reaching a model.
"""
from __future__ import annotations
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP2_INTERFACE_VERSION = 6
FROZEN_PROBLEMS = HERE / "frozen_assets" / "Problems_main.json"

# Fields on a problem record that must NEVER appear in a verifier prompt.
FORBIDDEN_PROBLEM_FIELDS = (
    "answer", "answer_rounded", "answer_detail", "reference_solution",
    "GOLD_VALUE_STATUS", "GOLD_VALUE_WARNING", "formulation_audit_specs",
    "checker_specs", "checker_functions", "audit_data", "source_metadata",
    "requirement_id_map",
)
# Token substrings that must not survive sanitization (defense in depth).
FORBIDDEN_TOKENS = (
    "gold", "reference_solution", "injected", "mutation", "mutant",
    "objective_value_is", "certified", "witness", "audit_", "checker",
)


class RequirementProvider:
    def __init__(self):
        self.source = "Problems_main.json"
        with FROZEN_PROBLEMS.open(encoding="utf-8") as handle:
            root = json.load(handle)
        self._problems = {int(p["id"]): p for p in
                          (root["pilot_problems"] if isinstance(root, dict) else root)}

    def problem(self, pid):
        return self._problems[int(pid)]

    def requirements(self, pid):
        """Return the frozen requirement list [{requirement_id, requirement_text, category}]
        for this problem. IDs and text only -- no probes, labels, or gold."""
        reqs = self._problems[int(pid)].get("requirements", [])
        return [{"requirement_id": r["requirement_id"],
                 "requirement_text": r.get("requirement_text", ""),
                 "category": r.get("category", "")}
                for r in reqs]

    def provenance(self, pid):
        return {"requirement_source": self.source,
                "n_requirements": len(self.requirements(pid))}


def _sanitize_text(s: str) -> str:
    """Strip answer-revealing phrases from a free-text field."""
    s = re.sub(r"the gold value is[^.;\n]*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"the answer is[^.;\n]*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"optimal (?:value|objective) is[^.;\n]*", "", s, flags=re.IGNORECASE)
    return s


def strip_code_annotations(code: str) -> str:
    """Remove the module docstring and comments from candidate code so bug annotations
    (e.g. a mutant annotation naming an injected requirement, or 'certified') never reach a
    verifier. Keeps
    executable logic intact -- this is what a real reviewer would see."""
    import ast
    try:
        tree = ast.parse(code)
        # drop module docstring
        if (tree.body and isinstance(tree.body[0], ast.Expr)
                and isinstance(getattr(tree.body[0], "value", None), ast.Constant)
                and isinstance(tree.body[0].value.value, str)):
            tree.body = tree.body[1:]
        # drop function/class docstrings too
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(getattr(node.body[0], "value", None), ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    node.body = node.body[1:]
        stripped = ast.unparse(tree)
    except SyntaxError:
        stripped = code
    # remove any remaining line comments
    out = []
    for line in stripped.splitlines():
        if "#" in line:
            # naive but safe: cut at first # not inside a string (candidate code is simple)
            in_str = None
            cut = None
            for i, ch in enumerate(line):
                if in_str:
                    if ch == in_str: in_str = None
                elif ch in "\"'":
                    in_str = ch
                elif ch == "#":
                    cut = i; break
            line = line[:cut].rstrip() if cut is not None else line
        out.append(line)
    return "\n".join(l for l in out if l.strip())


def build_candidate_prompt_payload(provider: RequirementProvider, pid, candidate_code: str):
    """Assemble the ONLY content a verifier may see, sanitized. Raises on residual leak."""
    problem = provider.problem(pid)
    candidate_code = strip_code_annotations(candidate_code)
    # problem description: question text only, sanitized; NEVER the forbidden fields
    description = _sanitize_text(str(problem.get("question", "")))
    # data instance is legitimately part of the candidate's problem; include it, but it must
    # not carry gold -- data_instance is model input, not the answer. Sanitize its strings.
    data_instance = json.loads(_sanitize_text(json.dumps(problem.get("data_instance", {}))))
    requirements = provider.requirements(pid)

    payload = {
        "problem_id": pid,
        "problem_description": description,
        "data_instance": data_instance,
        "requirements": requirements,       # id + text + category only
        "candidate_code": candidate_code,
    }

    # HARD CHECK: no forbidden token survives anywhere in the payload.
    blob = json.dumps(payload, ensure_ascii=False).lower()
    for tok in FORBIDDEN_TOKENS:
        if tok in blob:
            # allow the literal category word 'objective' (a legit requirement category) but
            # not 'gold'/'injected'/'mutation'/etc.
            if tok == "objective_value_is":
                continue
            raise RuntimeError(
                f"PROMPT LEAK GUARD: forbidden token '{tok}' present in verifier payload for "
                f"p{pid}. Refusing to build prompt. (This should never happen -- indicates a "
                f"leak in the candidate code or problem description.)")
    return payload


# Structured output schema every verifier prediction MUST conform to (validated by runner).
PREDICTION_SCHEMA_KEYS = ("verdict", "suspected_requirement_ids", "error_reason",
                          "predicted_taxonomy_category", "evidence", "confidence")
VALID_VERDICTS = ("correct", "incorrect", "pipeline_error")
TAXONOMY_ENUM = (
    "constraint_omission", "constraint_misspecification", "domain_or_bound_error",
    "linking_or_logic_error", "objective_accounting_error",
    "extra_or_overrestrictive_constraint", "mixed_or_unclear", "none",
)


def validate_prediction(pred: dict, valid_requirement_ids=None, *, parse_ok=True,
                        executed_fail_ids=None, allow_unlocalized_incorrect=False):
    """Return (ok, errors). Does not mutate. Enforces the full structured-output contract:
      - verdict in {correct, incorrect, pipeline_error}
      - every suspected requirement id exists in the supplied requirement list (if provided)
      - predicted_taxonomy_category in the frozen enum (blank is INVALID -> drives retry)
      - confidence parseable and within [0, 1]
      - error_reason AND evidence non-empty when verdict == incorrect
    """
    errs = []
    if not parse_ok:
        errs.append("parse_ok=false")
    if not isinstance(pred, dict):
        return False, ["prediction is not a dict"]
    for k in PREDICTION_SCHEMA_KEYS:
        if k not in pred:
            errs.append(f"missing key {k}")
    v = pred.get("verdict")
    if v not in VALID_VERDICTS:
        errs.append(f"verdict must be one of {VALID_VERDICTS}, got {v!r}")
    sus = pred.get("suspected_requirement_ids", [])
    if not isinstance(sus, list):
        errs.append("suspected_requirement_ids must be a list")
        sus = []
    if valid_requirement_ids is not None:
        valid_set = {str(x) for x in valid_requirement_ids}
        for rid in sus:
            # Reject nested/non-scalar IDs explicitly.  Do not attempt raw set membership on an
            # LLM-produced dict/list, which previously caused ``unhashable type: 'dict'``.
            if not isinstance(rid, (str, int, float, bool)) or str(rid) not in valid_set:
                errs.append(f"suspected id {rid!r} not in requirement list")
    tax = pred.get("predicted_taxonomy_category", "")
    if tax not in TAXONOMY_ENUM:
        errs.append(f"predicted_taxonomy_category {tax!r} not in frozen enum")
    conf = pred.get("confidence", "")
    try:
        cf = float(conf)
        if not (0.0 <= cf <= 1.0):
            errs.append(f"confidence {cf} outside [0,1]")
    except (TypeError, ValueError):
        errs.append(f"confidence {conf!r} not numeric")
    if v == "incorrect":
        if not sus and not allow_unlocalized_incorrect:
            errs.append("suspected_requirement_ids must be nonempty when verdict=incorrect")
        if tax == "none":
            errs.append("taxonomy cannot be none when verdict=incorrect")
        if not str(pred.get("error_reason", "")).strip():
            errs.append("error_reason required when verdict=incorrect")
        if not str(pred.get("evidence", "")).strip():
            errs.append("evidence required when verdict=incorrect")
    if v == "correct":
        if sus:
            errs.append("suspected_requirement_ids must be [] when verdict=correct")
        if tax != "none":
            errs.append("taxonomy must be none when verdict=correct")
    if v == "pipeline_error":
        if sus:
            errs.append("suspected_requirement_ids must be [] when verdict=pipeline_error")
        if tax != "none":
            errs.append("taxonomy must be none when verdict=pipeline_error")
    failed = [str(x) for x in (executed_fail_ids or [])]
    if failed:
        if v != "incorrect":
            errs.append("verdict must be incorrect when an executed probe failed")
        missing = [rid for rid in failed if rid not in sus]
        if missing:
            errs.append("failed probe requirement IDs missing from localization: " + ",".join(missing))
        if tax == "none":
            errs.append("taxonomy cannot be none when an executed probe failed")
    return len(errs) == 0, errs


if __name__ == "__main__":
    # self-check: gold list loads; comments/docstrings are removed; executable leaks fail.
    p = RequirementProvider("gold")
    print("p1 requirements:", [r["requirement_id"] for r in p.requirements(1)])
    print("provenance:", p.provenance(1))
    clean = build_candidate_prompt_payload(p, 1, "# gold objective is 43200\nprint(1)")
    assert "gold" not in json.dumps(clean).lower()
    print("annotation stripping OK")
    try:
        build_candidate_prompt_payload(p, 1, "gold_value = 43200\nprint(gold_value)")
        raise AssertionError("executable leak was not rejected")
    except RuntimeError:
        print("residual leak guard OK")
