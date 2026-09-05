#!/usr/bin/env python3
"""
Exp1 tested-model runner (Ollama/OpenAI; build_model + solve contract; Layer 1 + Layer 2).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROBLEMS_PATH = BASE_DIR / "Problems_main.json"
DEFAULT_CHECKERS_PATH = BASE_DIR / "checkers.py"
DEFAULT_AUDIT_PATH   = BASE_DIR / "formulation_audit.py"
DEFAULT_OUTPUT_DIR = BASE_DIR / "exp1_outputs"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODELS = ["gemma3:12b"]

PROMPT_VERSION = "v2"

FORMULATION_PROMPT_TEMPLATE = """You are an expert operations research modeler.

Write Python code using gurobipy that models and solves the optimization problem below.

Optimization problem:
{problem_text}

Your code MUST define exactly TWO functions.

1) def build_model(data: dict) -> tuple:
   - Build the Gurobi model: create ALL decision variables, ALL constraints, and the objective.
   - Do NOT call optimize() inside build_model.
   - Return exactly: return model, variables
   - `variables` is a dict whose keys are EXACTLY the variable keys listed below and whose
     values are the corresponding gurobipy Var objects (or dicts of Var objects). Use the
     key strings exactly as given; do not invent, rename, or nest them differently.
{model_contract}

2) def solve(data: dict) -> dict:
   - Call build_model(data), then call model.optimize().
   - Do NOT add, remove, or modify any variables, constraints, or the objective in solve().
     All model building happens in build_model(). solve() only optimizes and reads results.
   - Return a dict following this exact solution schema:
{solution_schema}

The `data` argument contains the numeric instance:
{data_instance}

Modeling rules:
- Use only gurobipy and the Python standard library.
- Read ALL numeric values from `data`; do not hard-code numbers from the problem text.
- Declare each variable's type (continuous / integer / binary) as appropriate to the problem.
- Do not read files. Do not access the network. Do not print anything.
- The returned solution keys must match the schema exactly.

Interface & API-hygiene rules (these are about correct code, not about the model's math):
- The `variables` dict must contain ONLY the required variable keys mapping to gurobipy Var
  objects (or dicts of Var objects). Do NOT put metadata in it: no `variables_keys`, `note`,
  `description`, `explanation`, comments, strings, or type labels as values.
- After model.optimize(), read results as attributes: `model.Status` and `model.ObjVal`
  (note the capitalization). Read a variable's value with `var.X`.
- Use only real gurobipy status constants: GRB.OPTIMAL, GRB.INFEASIBLE, GRB.UNBOUNDED,
  GRB.INF_OR_UNBD, GRB.TIME_LIMIT. Do NOT use names like GRB.INFEASIBLE_OR_UNBOUNDED,
  and do NOT call GRB.Status(...) or index GRB.Status — it is not callable.
- If you read a variable attribute such as VType or LB, call model.update() first.
- Do not call model.getVarByName(...) or model.getConstrByName(...) unless you have called
  model.update() and the variable/constraint is guaranteed to exist.
- To sum Var objects use gurobipy.quicksum(...); do not add a Var to a Python string.

Return ONLY raw Python code. No markdown fences, no explanations.
"""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_checkers_module(path):
    path = Path(path)
    spec = importlib.util.spec_from_file_location("frozen_checkers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "REGISTRY"):
        raise RuntimeError("checkers.py must define REGISTRY")
    return module


def get_problems(data):
    if isinstance(data, list):
        return data
    for key in ("pilot_problems", "problems"):
        if isinstance(data, dict) and key in data:
            return data[key]
    raise ValueError("Expected list or dict with 'pilot_problems'/'problems'.")


def parse_problem_ids(ids_str):
    ids_str = ids_str.strip()
    if ids_str.lower() in {"all", "*"}:
        return None
    return {int(x.strip()) for x in ids_str.split(",") if x.strip()}



# Keys that must NEVER reach the tested model. Stripped recursively from every prompt-facing
# object (solution_schema, model_contract, data_instance) before rendering. This makes prompt
# leakage structurally impossible even if a problem record carries such a field by mistake.
PROMPT_FORBIDDEN_KEYS = frozenset({
    "example", "examples", "reference_solution", "reference", "solution_example",
    "checker_functions", "checker_logic", "checker_specs",
    "formulation_audit_specs", "audit_specs", "audit_data", "audit_probes",
    "GOLD_VALUE_WARNING", "GOLD_VALUE_STATUS", "gold", "gold_objective",
    "answer", "answer_rounded", "optimal_value", "optimal_solution",
    "requirements", "requirement_id",
})

def _sanitize_for_prompt(obj):
    """Recursively drop forbidden keys from any dict/list so nothing leaks into the prompt.
    Returns a new object; does not mutate the input."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_prompt(v) for k, v in obj.items()
                if k not in PROMPT_FORBIDDEN_KEYS}
    if isinstance(obj, list):
        return [_sanitize_for_prompt(v) for v in obj]
    return obj

def build_prompt(problem):
    # NOTE: this function reads ONLY data_instance (raw, prompt-safe). It must never read
    # problem['audit_data'] (hidden derived ground-truth). Do not add audit_data here.
    # Render ONLY the variable-key schema and (optional) key-format note. This is format
    # information the tested model needs to return parsable variables; it must never carry
    # the mathematical formulation (no constraints, coefficients, or objective hints).
    mc = problem.get("model_contract", {})
    contract = {"variables_keys": mc.get("variables_keys", {})}
    note = mc.get("prompt_note") or mc.get("note")
    if note:
        contract["note"] = note
    # Sanitize EVERY prompt-facing object recursively so no gold/example/audit field can leak.
    safe_data = _sanitize_for_prompt(problem.get("data_instance", {}))
    safe_schema = _sanitize_for_prompt(problem["solution_schema"])
    safe_contract = _sanitize_for_prompt(contract)
    return FORMULATION_PROMPT_TEMPLATE.format(
        problem_text=problem["question"],
        data_instance=json.dumps(safe_data, indent=2, ensure_ascii=False),
        solution_schema=json.dumps(safe_schema, indent=2, ensure_ascii=False),
        model_contract=json.dumps(safe_contract, indent=2, ensure_ascii=False),
    )


def call_ollama(model, prompt, ollama_url, temperature, seed, request_timeout, num_predict,
                disable_think=True):
    options = {"temperature": temperature, "num_predict": num_predict}
    if seed is not None:
        options["seed"] = seed
    payload = {"model": model, "prompt": prompt, "stream": False, "options": options}
    if disable_think:
        # Thinking models (for example, deepseek-r1) can use most of num_predict on <think> blocks,
        # truncating the actual code ("missing solve", unterminated strings). Ollama >= 0.9
        # honors think=false; older servers may reject the field, so fall back gracefully.
        payload["think"] = False
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(ollama_url, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=request_timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if disable_think and e.code in (400, 422):
            return call_ollama(model, prompt, ollama_url, temperature, seed, request_timeout,
                               num_predict, disable_think=False)
        raise


def _usage_value(usage, *names):
    if usage is None:
        return ""
    for name in names:
        if isinstance(usage, dict) and name in usage:
            return usage.get(name, "")
        value = getattr(usage, name, "")
        if value != "":
            return value
    return ""


def call_openai(model, prompt, temperature, seed, request_timeout, num_predict):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment")
    try:
        from openai import OpenAI
        from openai import BadRequestError
    except ImportError as e:
        raise RuntimeError("OpenAI Python SDK is not installed. Run: pip install openai") from e
    client = OpenAI(api_key=api_key, timeout=request_timeout)
    request = {
        "model": model,
        "input": prompt,
        "max_output_tokens": num_predict,
    }
    if temperature is not None:
        request["temperature"] = temperature
    if seed is not None:
        request["seed"] = seed

    # Reasoning models (gpt-5-nano, o-series, ...) reject optional sampling params such as
    # `temperature` and `seed` (only the default temperature=1 is allowed). Rather than
    # hard-code which model rejects which field, we send the params and, if the API responds
    # with "Unsupported parameter: '<name>'", drop that field and retry. This mirrors the
    # Ollama `think=false` fallback and keeps a single code path for all providers.
    # It does NOT change temperature/seed for models that DO accept them.
    _optional = ("temperature", "seed", "max_output_tokens")
    while True:
        try:
            response = client.responses.create(**request)
            break
        except BadRequestError as e:
            msg = str(getattr(e, "message", "") or e)
            dropped = None
            for name in _optional:
                # match the API's "Unsupported parameter: 'temperature'" / "not supported"
                if name in request and name in msg and (
                        "unsupported" in msg.lower() or "not supported" in msg.lower()
                        or "unknown" in msg.lower()):
                    request.pop(name, None)
                    dropped = name
                    break
            if dropped is None:
                raise
            # loop and retry without the offending field
    raw_text = getattr(response, "output_text", None)
    if raw_text is None:
        parts = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text_part = getattr(content, "text", None)
                if text_part is not None:
                    parts.append(text_part)
        raw_text = "\n".join(parts)
    usage = getattr(response, "usage", None)
    # Reasoning models (gpt-5-nano, o-series) share max_output_tokens between hidden
    # reasoning and visible output. When reasoning consumes the budget, the API returns
    # status="incomplete" (reason="max_output_tokens") with an empty/partial output_text.
    # Surface that here so the run row can flag truncation instead of misreading a
    # token-starved response as "model produced no code". Diagnostic only; no label logic.
    status = getattr(response, "status", None)
    incomplete = getattr(response, "incomplete_details", None)
    incomplete_reason = getattr(incomplete, "reason", None) if incomplete else None
    reasoning_tokens = ""
    try:
        details = getattr(usage, "output_tokens_details", None)
        reasoning_tokens = _usage_value(details, "reasoning_tokens")
    except Exception:
        pass
    return {
        "response": raw_text or "",
        "prompt_eval_count": _usage_value(usage, "input_tokens", "prompt_tokens"),
        "eval_count": _usage_value(usage, "output_tokens", "completion_tokens"),
        "openai_status": status or "",
        "openai_incomplete_reason": incomplete_reason or "",
        "openai_reasoning_tokens": reasoning_tokens,
    }


def _strip_think_blocks(text):
    """Remove <think>...</think> reasoning blocks emitted by thinking models (for example,
    deepseek-r1). Also drop an UNCLOSED trailing <think> block (truncated output)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # unclosed think block: everything from a dangling <think> to EOF is reasoning, not code
    text = re.sub(r"<think>.*\Z", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text


def _looks_like_python(block):
    return bool(re.search(r"^\s*(import|from|def|class)\s", block, flags=re.MULTILINE))


def extract_python_code(text):
    """Back-compat wrapper: returns extracted code only (see extract_python_code_ex)."""
    return extract_python_code_ex(text)[0]


def extract_python_code_ex(text):
    """Robust extraction addressing observed small-model failure signatures:
    1. prose before/around fenced code           -> take fenced blocks only
    2. TRUNCATED output with an unclosed fence   -> capture from the dangling fence to EOF
    3. build_model and solve in SEPARATE fences  -> concatenate python-looking blocks
    4. no fences at all, prose then raw code     -> slice from the first import/from/def line
    5. <think> reasoning blocks                  -> stripped first
    Never returns leading prose as code."""
    text = _strip_think_blocks(text).strip()

    # closed fenced blocks
    blocks = re.findall(r"```(?:python|py)?\s*\n?(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    # a dangling (unclosed) final fence: opening ``` with no closing pair after it
    n_fences = len(re.findall(r"```", text))
    if n_fences % 2 == 1:
        last_open = text.rfind("```")
        tail = re.sub(r"^```(?:python|py)?\s*\n?", "", text[last_open:], flags=re.IGNORECASE)
        if tail.strip():
            blocks.append(tail)

    _dangling = n_fences % 2 == 1
    py_blocks = [b.strip() for b in blocks if _looks_like_python(b)]
    if py_blocks:
        # If the needed functions are split across blocks, concatenate; else prefer the block
        # holding build_model, else the longest.
        joined = "\n\n".join(py_blocks)
        has_bm = [b for b in py_blocks if "def build_model" in b]
        has_sv = [b for b in py_blocks if "def solve" in b]
        if has_bm and has_sv and not (set(map(id, has_bm)) & set(map(id, has_sv))):
            return joined, "recovered_split_blocks"
        if len(py_blocks) > 1 and "def build_model" in joined and "def solve" in joined:
            return joined, "recovered_split_blocks"
        if has_bm:
            code = max(has_bm, key=len)
        else:
            code = max(py_blocks, key=len)
        return code, ("recovered_unclosed_fence" if _dangling else "clean_fenced")

    # No usable fences: fall back to slicing from the first code-looking line so that leading
    # prose is never written into the .py file.
    m = re.search(r"^\s*(import|from|def|class)\s", text, flags=re.MULTILINE)
    if m:
        code = text[m.start():]
        code = re.sub(r"```\s*$", "", code).strip()
        # Small models often emit the SAME model 2-3 times with prose in between
        # ("Let me reconsider...\n\nimport gurobipy..."), so a single slice can splice
        # prose into the middle -> SyntaxError / missing build_model. If the naive slice
        # doesn't compile, recover the largest COMPILABLE region that still defines both
        # build_model and solve, preferring the LAST such copy (the model's final answer).
        def _compiles(src):
            try:
                compile(src, "<extract>", "exec"); return True
            except SyntaxError:
                return False
        if not _compiles(code) or "def build_model" not in code or "def solve" not in code:
            # candidate start offsets: every top-level import/def/class line
            starts = [mm.start() for mm in
                      re.finditer(r"^\s*(import|from|def|class)\s", code, flags=re.MULTILINE)]
            best = None
            for si in starts:
                seg = code[si:].strip()
                seg = re.sub(r"```.*$", "", seg, flags=re.DOTALL).strip()
                if "def build_model" in seg and "def solve" in seg and _compiles(seg):
                    best = seg  # keep scanning; later starts -> later (final) copy
            if best is not None:
                return best, "recovered_prose_slice_recompiled"
            # try trimming trailing prose line-by-line from the end until it compiles
            lines = code.splitlines()
            for cut in range(len(lines), 0, -1):
                seg = "\n".join(lines[:cut]).strip()
                if "def build_model" in seg and "def solve" in seg and _compiles(seg):
                    return seg, "recovered_prose_slice_trimmed"
        return code, "recovered_prose_slice"
    # nothing code-like at all -> empty so it is classified as contract_failure with a clear
    # "no python code found" signal instead of a prose SyntaxError.
    return "", "no_code_found"


def validate_solution_schema(result, solution_schema):
    errors = []
    if not isinstance(result, dict):
        return False, [f"result is not a dict: {type(result).__name__}"]
    for key in solution_schema.get("required", []):
        if key not in result:
            errors.append(f"missing top-level key: {key}")
    for key in ["status", "objective", "solution"]:
        if key not in result:
            errors.append(f"missing required experiment key: {key}")
    if "solution" in result and not isinstance(result["solution"], dict):
        errors.append("result['solution'] is not a dict")
        return False, errors
    sol_schema = solution_schema.get("properties", {}).get("solution", {})
    for key in sol_schema.get("required", []):
        if isinstance(result.get("solution"), dict) and key not in result["solution"]:
            errors.append(f"missing solution key: {key}")
    return len(errors) == 0, errors


_SOLVE_WRAPPER = r"""
import importlib.util, inspect, json, sys
from pathlib import Path

code_path = Path(sys.argv[1]); data_path = Path(sys.argv[2])
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

spec = importlib.util.spec_from_file_location("generated_model", code_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

has_solve = hasattr(module, "solve") and callable(getattr(module, "solve", None))
has_build = hasattr(module, "build_model") and callable(getattr(module, "build_model", None))

if not has_build:
    print(json.dumps({
        "__contract_error__": "missing required function build_model(data)",
        "has_build_model": False
    }))
    raise SystemExit(0)

if not has_solve:
    print(json.dumps({
        "__contract_error__": "missing required function solve(data)",
        "has_build_model": has_build
    }))
    raise SystemExit(0)

try:
    inspect.signature(module.build_model).bind(data)
except TypeError as e:
    print(json.dumps({
        "__contract_error__": "build_model must be callable as build_model(data): " + str(e),
        "has_build_model": has_build
    }))
    raise SystemExit(0)

try:
    inspect.signature(module.solve).bind(data)
except TypeError as e:
    print(json.dumps({
        "__contract_error__": "solve must be callable as solve(data): " + str(e),
        "has_build_model": has_build
    }))
    raise SystemExit(0)

result = module.solve(data)

def make_jsonable(x):
    if isinstance(x, dict):  return {str(k): make_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [make_jsonable(v) for v in x]
    if hasattr(x, "item"):
        try: return make_jsonable(x.item())
        except Exception: pass
    try:
        json.dumps(x); return x
    except TypeError:
        try: return float(x)
        except Exception: return str(x)

print(json.dumps({"__result__": make_jsonable(result), "has_build_model": has_build}))
"""
def run_generated_code(code, data_instance, timeout_seconds, work_dir):
    (work_dir / "generated_model.py").write_text(code, encoding="utf-8")
    (work_dir / "data_instance.json").write_text(json.dumps(data_instance, ensure_ascii=False), encoding="utf-8")
    (work_dir / "execute_generated.py").write_text(_SOLVE_WRAPPER, encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(work_dir / "execute_generated.py"),
             str(work_dir / "generated_model.py"), str(work_dir / "data_instance.json")],
            cwd=str(work_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return None, "timeout", f"solve exceeded {timeout_seconds}s", False
    if completed.returncode != 0:
        err = completed.stderr.strip()[-4000:]
        if "SyntaxError" in err or "IndentationError" in err:
            return None, "syntax_error", err, False
        return None, "runtime_error", err, False
    out = completed.stdout.strip()
    if not out:
        return None, "no_output", "solve printed no JSON", False
    try:
        payload = json.loads(out.splitlines()[-1])
    except json.JSONDecodeError as e:
        return None, "json_parse_error", f"{e}; stdout={out[-2000:]}", False
    if "__contract_error__" in payload:
        return None, "contract_failure", payload["__contract_error__"], payload.get("has_build_model", False)
    return payload["__result__"], "", "", payload.get("has_build_model", False)


def _checker_kind(fn_name):
    if fn_name.endswith("_opt"):  return "objective_opt"
    if fn_name.endswith("_coef"): return "objective_coef"
    return "requirement"


def checker_key(problem):
    """Registry/audit key for a problem. The frozen checkers.py and
    formulation_audit specs are keyed to ORIGINAL problem ids. When a renumbered
    subset is run (ids resequenced 1..N with original_problem_id preserved), all
    checker/audit/gold lookups MUST use the original id, or a new id N would
    silently match a DIFFERENT problem's checkers (pN) and mislabel every run.
    Falls back to `id` for the full, non-renumbered bank."""
    oid = problem.get("original_problem_id", problem.get("id"))
    return f"p{int(oid)}", int(oid)


def run_checkers(checkers_module, problem_id, data_instance, result):
    registry = checkers_module.REGISTRY.get(f"p{problem_id}")
    if registry is None:
        return [{"requirement_id": None, "checker_id": None, "status": "FAIL",
                 "detail": f"no registry for p{problem_id}", "checker_kind": "registry_error"}]
    rows = []
    for req_id, entries in registry.items():
        for checker_id, fn in entries:
            fn_name = getattr(fn, "__name__", "unknown")
            try:
                status, detail = fn(data_instance, result)
            except Exception as e:
                status, detail = "FAIL", f"checker exception: {type(e).__name__}: {e}"
            rows.append({"requirement_id": req_id, "checker_id": checker_id,
                         "checker_function": fn_name, "status": status, "detail": detail,
                         "checker_kind": _checker_kind(fn_name)})
    return rows


def infer_objective_match(checker_rows, result, gold_answer):
    opt = [r for r in checker_rows if r.get("checker_kind") == "objective_opt"]
    if opt:
        return all(r["status"] == "PASS" for r in opt)
    try:
        # combined relative+absolute tolerance (see checkers.objective_close): absorbs
        # gold rounding without admitting genuine objective errors.
        rec = float(result.get("objective")); gold = float(gold_answer)
        return abs(rec - gold) <= max(0.01, 1e-6 * abs(gold))
    except Exception:
        return False


def classify(objective_match, checker_rows):
    """Label from Layer-1 signals only (Layer-2 promotion happens later in main()).

    Rule (revised): Layer-1 requirement checkers are DIAGNOSTIC checks that reveal whether an
    objective-correct answer is actually wrong. An objective-only evaluator would miss such a
    case, so a failing requirement checker on an objective-correct run is a silent bug.

      objective_match=False                            -> loud_bug
      objective_match=True, no failing requirement     -> correct
      objective_match=True, >=1 failing requirement    -> silent_bug

    Ambiguity-FLAGGED requirement checkers never flip the label (they encode a legitimate
    ambiguity in the gold, not a model error). objective_coef / objective_opt checks are
    excluded here (they are not `requirement` kind), so an objective-coefficient mismatch
    cannot masquerade as a silent bug.
    """
    failed_reqs = [r for r in checker_rows
                   if r["status"] != "PASS"
                   and r.get("checker_kind") == "requirement"
                   and not r.get("flagged", False)]
    if not objective_match:
        return "loud_bug"
    if failed_reqs:
        return "silent_bug"
    return "correct"


# ---------------------------------------------------------------------------
# Silent-bug TYPE taxonomy (shared by Exp 1 and Exp 2 -- Exp_2.py imports these).
# Exactly 4 broad categories + unknown_or_mixed, mapped from the violated
# requirement's `category` field in problems_main.json.
# ---------------------------------------------------------------------------
_DOMAIN_CATEGORIES = {"integrality", "non_negativity", "integer_domain", "domain",
                      "domain_bounds", "domain_bound", "binary_bound", "lower_bound"}
_LINKING_LOGIC_CATEGORIES = {"fixed_charge_link", "semicontinuous_min",
                             "logical_implication", "logical_disjunction", "cardinality",
                             "capacity_linking", "variable_fixing", "substitution",
                             "setup_fixed_cost", "prerequisite", "semi_continuous",
                             "linking_or_logic_error"}
_OBJECTIVE_CATEGORIES = {"objective", "objective_accounting", "objective_optimality",
                         "preference_goal"}

_BROAD_TYPES = ("domain_relaxation", "structural_constraint_error",
                "linking_or_logic_error", "objective_or_solution_error")


def _category_to_broad_type(category):
    if category in _DOMAIN_CATEGORIES:
        return "domain_relaxation"
    if category in _LINKING_LOGIC_CATEGORIES:
        return "linking_or_logic_error"
    if category in _OBJECTIVE_CATEGORIES:
        return "objective_or_solution_error"
    return "structural_constraint_error"


def silent_bug_type(failed_requirement_rows, formulation_violation_ids, problem):
    """Classify a silent_bug into ONE of 4 broad categories (+ unknown_or_mixed) and list
    the affected requirements.

    Returns (silent_bug_type, silent_bug_requirements_string).

    Categories:
      domain_relaxation           - integrality/binary relaxed, or nonnegativity/domain bound wrong
      structural_constraint_error - ordinary constraint missing/weak/wrong-direction (balance,
                                    capacity, covering, quality, inventory target, ...)
      linking_or_logic_error      - fixed-charge/setup/activation link, semicontinuous minimum,
                                    prerequisite/implication, either-or, at-most-k
      objective_or_solution_error - objective-accounting requirement violated (rare: objective
                                    checks are mostly excluded from silent-bug triggering by the
                                    objective_coef guard; this fires only for `objective`-category
                                    requirements)
      unknown_or_mixed            - multiple distinct categories implicated, or undeterminable
    """
    cat_by_id = {r["requirement_id"]: r.get("category", "")
                 for r in problem.get("requirements", [])}
    canonical = build_requirement_resolver(problem)
    l1_ids = [r.get("requirement_id") for r in failed_requirement_rows if r.get("requirement_id")]
    l2_ids = [rid for rid in (formulation_violation_ids or []) if rid]
    l2_only = [rid for rid in l2_ids if rid not in l1_ids]
    parts = list(dict.fromkeys(l1_ids))
    req_str = ",".join(parts)
    if l2_only:
        req_str = (req_str + " + " if req_str else "") + "fviol:" + ",".join(dict.fromkeys(l2_only))
    all_ids = list(dict.fromkeys(l1_ids + l2_ids))
    causes = {_category_to_broad_type(cat_by_id.get(canonical(rid), "")) for rid in all_ids}
    if not causes:
        return "unknown_or_mixed", req_str
    if len(causes) == 1:
        return next(iter(causes)), req_str
    return "unknown_or_mixed", req_str



# 7-bucket requirement taxonomy for frequency analysis (spec allows max 6-8 buckets).
# v3: extended to cover every category observed in problems_main_v3 (previously ~20
# categories -- incl. time_window with 200 requirements -- silently fell through to
# the quality_ratio_objective default, distorting the frequency taxonomy). A 7th
# bucket `scheduling_sequencing` was added because problems 59-93 are dominated by
# time-window / precedence / subtour structure that fits none of the original six.
# Buckets aggregate requirement CATEGORIES; frequency counting is done per failed
# requirement EVENT (one row per failed requirement per silent run), so the taxonomy
# reflects which requirement kinds actually fail, not which problems are big.
TAXONOMY = {
    # -- demand_or_coverage
    "covering": "demand_or_coverage", "coverage": "demand_or_coverage",
    "demand_satisfaction": "demand_or_coverage", "demand": "demand_or_coverage",
    "assignment": "demand_or_coverage", "category_counting": "demand_or_coverage",
    # -- capacity_or_resource
    "resource_capacity": "capacity_or_resource", "arc_capacity": "capacity_or_resource",
    "capacity": "capacity_or_resource", "budget": "capacity_or_resource",
    "piecewise_tier": "capacity_or_resource",
    "bottleneck_constraint": "capacity_or_resource",
    "workforce_change_limit": "capacity_or_resource",
    # -- balance_or_inventory
    "flow_balance": "balance_or_inventory", "inventory_balance": "balance_or_inventory",
    "inventory_target": "balance_or_inventory", "final_inventory": "balance_or_inventory",
    "cash_flow_balance": "balance_or_inventory", "balance": "balance_or_inventory",
    "conservation_linking": "balance_or_inventory",
    # -- domain_or_integrality
    "integrality": "domain_or_integrality", "non_negativity": "domain_or_integrality",
    "integer_domain": "domain_or_integrality", "domain": "domain_or_integrality",
    "domain_bounds": "domain_or_integrality", "domain_bound": "domain_or_integrality",
    "binary_bound": "domain_or_integrality", "lower_bound": "domain_or_integrality",
    # -- linking_setup_logic
    "fixed_charge_link": "linking_setup_logic", "semicontinuous_min": "linking_setup_logic",
    "logical_implication": "linking_setup_logic", "logical_disjunction": "linking_setup_logic",
    "cardinality": "linking_setup_logic", "capacity_linking": "linking_setup_logic",
    "variable_fixing": "linking_setup_logic", "substitution": "linking_setup_logic",
    "setup_fixed_cost": "linking_setup_logic", "prerequisite": "linking_setup_logic",
    "semi_continuous": "linking_setup_logic",
    # 'linking_or_logic_error' is a broad-type name mistakenly used as a category in
    # 30 requirements (flagged in human_review_needed.md); mapped here so events
    # land in the right bucket even before the label is corrected upstream.
    "linking_or_logic_error": "linking_setup_logic",
    # -- scheduling_sequencing (new in v3)
    "time_window": "scheduling_sequencing", "precedence": "scheduling_sequencing",
    "subtour_elimination": "scheduling_sequencing",
    "makespan_bound": "scheduling_sequencing",
    "disjunctive_no_overlap": "scheduling_sequencing",
    "production_blackout": "scheduling_sequencing",
    # -- quality_ratio_objective
    "blending_quality": "quality_ratio_objective", "ratio_proportion": "quality_ratio_objective",
    "objective": "quality_ratio_objective", "objective_optimality": "quality_ratio_objective",
    "objective_accounting": "quality_ratio_objective",
    "preference_goal": "quality_ratio_objective",
}
TAXONOMY6 = TAXONOMY  # backward-compat alias (pre-v3 name)
TAXONOMY_FALLBACK_BUCKET = "quality_ratio_objective"


def taxonomy6(category):
    """Bucket lookup. Unknown categories fall back (and are surfaced by
    validate_exp1_assets.py as warnings so the table above stays exhaustive)."""
    return TAXONOMY.get(category, TAXONOMY_FALLBACK_BUCKET)


# 7-category general-mechanism taxonomy (report-level). Self-contained here so the runner
# emits it into results.csv directly; report_taxonomy.py holds the same crosswalk for the
# analyzer. Categories: constraint_omission, constraint_misspecification,
# domain_or_bound_error, linking_or_logic_error, objective_accounting_error,
# over_restrictive_constraint, mixed_or_unclear.
_RC_DOMAIN = {"integrality", "non_negativity", "integer_domain", "domain",
              "domain_bounds", "domain_bound", "binary_bound", "lower_bound"}
_RC_LINKING = {"fixed_charge_link", "semicontinuous_min", "logical_implication",
               "logical_disjunction", "cardinality", "capacity_linking", "variable_fixing",
               "substitution", "setup_fixed_cost", "prerequisite", "semi_continuous",
               "linking_or_logic_error"}
_RC_OBJECTIVE = {"objective", "objective_accounting", "objective_optimality", "preference_goal"}


def _report_category(category, direction=None, witness_bounded=None):
    """Map one failed-requirement's category (+optional audit direction) to one of the 7
    general-mechanism report categories. Domain/linking/objective map by family; structural
    families split by direction: model_rejects_feasible -> over_restrictive_constraint;
    model_accepts_forbidden -> constraint_omission (inert) or constraint_misspecification
    (some structure present); direction unknown -> constraint_misspecification (conservative,
    never claims over-restriction from a Layer-1-only signal)."""
    cat = category or ""
    if cat in _RC_DOMAIN:
        return "domain_or_bound_error"
    if cat in _RC_LINKING:
        return "linking_or_logic_error"
    if cat in _RC_OBJECTIVE:
        return "objective_accounting_error"
    if direction == "model_rejects_feasible":
        return "over_restrictive_constraint"
    if direction == "model_accepts_forbidden":
        return "constraint_omission" if witness_bounded is False else "constraint_misspecification"
    return "constraint_misspecification"


def build_requirement_resolver(problem):
    """Return canonical(rid) mapping any checker/audit requirement id to the AUTHORED
    requirement id it instantiates: exact match first, then the problem's frozen
    requirement_id_map (built by fix_exp1_assets.py), then a conservative
    numeric/roman/day suffix strip as last resort. Guarantees category lookups and
    frequency events aggregate at authored granularity instead of dropping to ''.
    """
    authored = {r["requirement_id"] for r in problem.get("requirements", [])}
    rid_map = problem.get("requirement_id_map", {}) or {}
    _suffix = re.compile(r"_(?:\d+|[IVX]+|Mon|Tue|Wed|Thu|Fri|Sat|Sun|s\d+|c\d+|q\d+|t\d+)$")

    def canonical(rid):
        if rid is None:
            return rid
        rid = str(rid)
        if rid in authored:
            return rid
        if rid in rid_map:
            return rid_map[rid]
        cur = rid
        while True:
            nxt = _suffix.sub("", cur)
            if nxt == cur:
                break
            cur = nxt
            if cur in authored:
                return cur
        return rid  # unresolved: keep raw id (validator flags these)
    return canonical


def _req_id_from_checker_id(checker_id):
    """checker ids look like 'p6.R7.C1' -> requirement id 'R7' (middle segments)."""
    parts = str(checker_id).split(".")
    return ".".join(parts[1:-1]) if len(parts) >= 3 else str(checker_id)


def silent_bug_source(failed_requirement_check_count, formulation_violation_count):
    """Which detection layer(s) established the silent bug. 'none' when not a silent bug."""
    if failed_requirement_check_count and formulation_violation_count:
        return "solution_and_formulation"
    if failed_requirement_check_count:
        return "solution_only"
    if formulation_violation_count:
        return "formulation_only"
    return "none"


def requirement_count_columns(problem, checkers_module):
    """Per-problem diagnostic-surface counts, attached to EVERY row (incl. correct rows) so
    silent-bug rate can later be regressed against requirement count.

    total_requirement_count            = intended requirements in the problem record
    layer1_requirement_count           = distinct requirement ids with >=1 `requirement`-kind
                                         checker in checkers.REGISTRY
    layer2_active_probe_count          = audit specs excluding not_probeable / layer1_only
    total_diagnostic_requirement_count = layer1 + layer2
    """
    total = len(problem.get("requirements", []))
    pkey, _ = checker_key(problem)
    reg = checkers_module.REGISTRY.get(pkey, {}) if checkers_module else {}
    canonical = build_requirement_resolver(problem)
    l1 = 0
    canon_l1 = set()
    for req_id, entries in reg.items():
        if any(_checker_kind(getattr(fn, "__name__", "")) == "requirement" for _, fn in entries):
            l1 += 1
            canon_l1.add(canonical(req_id))
    l2 = sum(1 for s in problem.get("formulation_audit_specs", [])
             if s.get("type") not in ("not_probeable", "layer1_only"))
    return {"total_requirement_count": total,
            "layer1_requirement_count": l1,
            "canonical_layer1_requirement_count": len(canon_l1),
            "layer2_active_probe_count": l2,
            "total_diagnostic_requirement_count": l1 + l2}


_AUDIT_WRAPPER_TEMPLATE = r'''
import importlib.util, json, sys
from pathlib import Path
sys.path.insert(0, {audit_dir!r})
import formulation_audit as FA
spec = importlib.util.spec_from_file_location("generated_model", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
if not hasattr(mod, "build_model"):
    print(json.dumps({{"__audit_error__": "generated code does not define build_model"}})); raise SystemExit(0)
data = json.load(open(sys.argv[2])); specs = json.load(open(sys.argv[3]))
try:
    rows = FA.run_formulation_audit(mod.build_model, data, specs)
    print(json.dumps({{"__rows__": rows}}))
except Exception as e:
    print(json.dumps({{"__audit_error__": "{{}}: {{}}".format(type(e).__name__, e)}}))
'''


def run_formulation_audit_subprocess(data_instance, specs, audit_module_path, timeout_seconds, work_dir):
    (work_dir / "audit_specs.json").write_text(json.dumps(specs), encoding="utf-8")
    wrapper = _AUDIT_WRAPPER_TEMPLATE.format(audit_dir=str(Path(audit_module_path).parent))
    (work_dir / "run_audit.py").write_text(wrapper, encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(work_dir / "run_audit.py"),
             str(work_dir / "generated_model.py"), str(work_dir / "data_instance.json"),
             str(work_dir / "audit_specs.json")],
            cwd=str(work_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return None, "audit_timeout"
    if completed.returncode != 0:
        return None, "audit_crash: " + completed.stderr.strip()[-1500:]
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except Exception as e:
        return None, f"audit_parse_error: {e}"
    if "__audit_error__" in payload:
        return None, payload["__audit_error__"]
    return payload["__rows__"], ""


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# Canonical results.csv column order. Shared by the final writer (write_csv) and the live
# incremental writer (LiveResultsWriter) so the live file and the end-of-run file are
# structurally identical. Adding a column here updates both paths at once.
RESULTS_FIELDNAMES = ["run_id", "model", "problem_id", "original_problem_id", "sample", "label", "raw_label", "final_label",
                  "extraction_mode", "code_ran", "schema_ok",
                  "objective_match", "has_build_model", "failed_checks", "failed_requirement_checks",
                  "formulation_violations", "flagged_formulation_violations", "audit_error",
                  "generated_code_path", "raw_response_path", "prompt_hash",
                  "prompt_version", "response_time_sec", "prompt_eval_count", "eval_count", "output_truncated",
                  "silent_bug_type", "silent_bug_requirements", "silent_bug_source", "report_categories",
                  "total_requirement_count", "layer1_requirement_count", "canonical_layer1_requirement_count",
                  "layer2_active_probe_count", "total_diagnostic_requirement_count",
                  "failed_requirement_check_count", "formulation_violation_count",
                  "total_violation_count", "error_type", "error_detail"]


def _normalize_labels(row):
    """Fill final_label/raw_label defaults exactly as write_csv did. Applied per-row so the
    live file matches the final file. Does NOT change any label VALUE that is already set."""
    if not row.get("final_label"):
        row["final_label"] = row.get("label", "")
    if not row.get("raw_label"):
        row["raw_label"] = row.get("final_label", "")
    return row


class LiveResultsWriter:
    """Appends each finished run row to results.csv and flushes to disk immediately, so a
    long run is inspectable/recoverable mid-flight. Writes the header once. Uses the same
    RESULTS_FIELDNAMES as the final write_csv, so switching to live writing changes only
    WHEN rows are written, never their content, columns, or order. The end-of-run write_csv
    still runs and produces a byte-equivalent file (idempotent)."""
    def __init__(self, path):
        self.path = Path(path)
        self._f = open(self.path, "w", encoding="utf-8", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=RESULTS_FIELDNAMES)
        self._w.writeheader()
        self._f.flush()
        try:
            os.fsync(self._f.fileno())
        except (OSError, ValueError):
            pass

    def append(self, row):
        _normalize_labels(row)
        self._w.writerow({k: row.get(k, "") for k in RESULTS_FIELDNAMES})
        self._f.flush()
        try:
            os.fsync(self._f.fileno())   # force to disk so a crash keeps completed rows
        except (OSError, ValueError):
            pass

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass


def write_csv(path, rows):
    for r in rows:
        _normalize_labels(r)
    fieldnames = RESULTS_FIELDNAMES
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})




def write_analysis_outputs(out_dir, summary_rows, problems_by_id, checkers_module):
    """Write the six analysis CSVs from the run's summary rows.

    silent_bug_requirement_events.csv is the frequency-analysis backbone: ONE ROW PER FAILED
    REQUIREMENT per silent run (a silent run failing 3 requirements yields 3 event rows), so
    taxonomy counts reflect requirement-failure frequency, not per-problem aggregates.
    """
    import csv as _csv
    from collections import Counter, defaultdict as _dd
    out = Path(out_dir)

    def _w(path, fields, rows):
        with open(out / path, "w", newline="", encoding="utf-8") as f:
            w = _csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fields})

    # ---- summary_by_problem.csv ----
    per = _dd(lambda: Counter())
    for r in summary_rows:
        per[r["problem_id"]][r.get("final_label", r.get("label"))] += 1
    rows = []
    for pid in sorted(per):
        c = per[pid]
        problem = problems_by_id.get(pid, {})
        counts = requirement_count_columns(problem, checkers_module) if problem else {}
        obj_ok = c["correct"] + c["silent_bug"]
        rows.append({"problem_id": pid, "scenario_id": problem.get("scenario_id", ""),
                     "n_runs": sum(c.values()), "correct": c["correct"],
                     "silent_bug": c["silent_bug"], "loud_bug": c["loud_bug"],
                     "code_failure": c["code_failure"], "schema_failure": c["schema_failure"],
                     "contract_failure": c["contract_failure"],
                     "audit_inconclusive": c["audit_inconclusive"],
                     "objective_correct_runs": obj_ok,
                     "silent_rate_among_objective_correct":
                         round(c["silent_bug"] / obj_ok, 4) if obj_ok else "",
                     **counts})
    if rows:
        _w("summary_by_problem.csv", list(rows[0].keys()), rows)

    silent = [r for r in summary_rows
              if r.get("final_label", r.get("label")) == "silent_bug"]

    # ---- silent_bug_rows.csv (full rows) ----
    if summary_rows:
        allkeys = list(summary_rows[0].keys())
        _w("silent_bug_rows.csv", allkeys, silent)

    # ---- silent_bug_requirement_events.csv: ONE ROW PER FAILED REQUIREMENT ----
    # v3: events aggregate at CANONICAL (authored) requirement granularity via
    # requirement_id_map, so a run that trips R_dem_s1..s4 yields ONE event for
    # R_demand (raw ids preserved in raw_requirement_ids). This keeps the frequency
    # taxonomy per-requirement rather than per-instantiated-row, and fixes the
    # category='' fallthrough that previously mis-bucketed every expanded id.
    events = []
    for r in silent:
        pid = r["problem_id"]
        problem = problems_by_id.get(pid, {})
        cat_by = {q["requirement_id"]: q.get("category", "")
                  for q in problem.get("requirements", [])}
        canonical = build_requirement_resolver(problem)
        l1_reqs, raw_by_canon = {}, {}
        for cid in filter(None, str(r.get("failed_requirement_checks", "")).split(",")):
            raw = _req_id_from_checker_id(cid)
            can = canonical(raw)
            l1_reqs.setdefault(can, []).append(cid)
            raw_by_canon.setdefault(can, set()).add(raw)
        l2_reqs = {}
        for raw in filter(None, str(r.get("formulation_violations", "")).split(",")):
            can = canonical(raw)
            l2_reqs.setdefault(can, set()).add(raw)
            raw_by_canon.setdefault(can, set()).add(raw)
        for rid in sorted(set(l1_reqs) | set(l2_reqs)):
            layer = ("both" if rid in l1_reqs and rid in l2_reqs
                     else "solution" if rid in l1_reqs else "formulation")
            cat = cat_by.get(rid, "")
            events.append({"run_id": r.get("run_id", ""), "model": r.get("model", ""),
                           "problem_id": pid, "requirement_id": rid,
                           "raw_requirement_ids": ";".join(sorted(raw_by_canon.get(rid, []))),
                           "category": cat, "taxonomy_bucket": taxonomy6(cat),
                           "detection_layer": layer,
                           "checker_ids": ";".join(l1_reqs.get(rid, [])),
                           "silent_bug_type": r.get("silent_bug_type", ""),
                           "silent_bug_source": r.get("silent_bug_source", "")})
    _w("silent_bug_requirement_events.csv",
       ["run_id", "model", "problem_id", "requirement_id", "raw_requirement_ids",
        "category", "taxonomy_bucket",
        "detection_layer", "checker_ids", "silent_bug_type", "silent_bug_source"], events)

    # ---- silent_bug_category_counts.csv (raw + per-problem-normalized) ----
    bc = _dd(lambda: {"events": 0, "reqs": set(), "probs": set()})
    for ev in events:
        b = bc[ev["taxonomy_bucket"]]
        b["events"] += 1
        b["reqs"].add((ev["problem_id"], ev["requirement_id"]))
        b["probs"].add(ev["problem_id"])
    tot = sum(b["events"] for b in bc.values()) or 1
    _w("silent_bug_category_counts.csv",
       ["taxonomy_bucket", "event_count", "event_share", "distinct_requirements",
        "distinct_problems", "events_per_problem"],
       [{"taxonomy_bucket": k, "event_count": v["events"],
         "event_share": round(v["events"] / tot, 4),
         "distinct_requirements": len(v["reqs"]), "distinct_problems": len(v["probs"]),
         "events_per_problem": round(v["events"] / len(v["probs"]), 3) if v["probs"] else ""}
        for k, v in sorted(bc.items())])

    # ---- requirement_failure_frequency.csv ----
    silent_runs_by_pid = Counter(r["problem_id"] for r in silent)
    rf = Counter((ev["problem_id"], ev["requirement_id"]) for ev in events)
    cat_lookup = {}
    for ev in events:
        cat_lookup[(ev["problem_id"], ev["requirement_id"])] = (ev["category"],
                                                                ev["taxonomy_bucket"])
    _w("requirement_failure_frequency.csv",
       ["problem_id", "requirement_id", "category", "taxonomy_bucket",
        "silent_event_count", "silent_runs_for_problem", "failure_rate_within_silent_runs"],
       [{"problem_id": pid, "requirement_id": rid,
         "category": cat_lookup[(pid, rid)][0], "taxonomy_bucket": cat_lookup[(pid, rid)][1],
         "silent_event_count": n, "silent_runs_for_problem": silent_runs_by_pid[pid],
         "failure_rate_within_silent_runs":
             round(n / silent_runs_by_pid[pid], 4) if silent_runs_by_pid[pid] else ""}
        for (pid, rid), n in sorted(rf.items())])

    # ---- failure_subtypes.csv ----
    fs = Counter()
    for r in summary_rows:
        fs[(r.get("final_label", r.get("label")), r.get("raw_label", ""),
            r.get("error_type", ""), r.get("extraction_mode", ""),
            str(r.get("output_truncated", "")))] += 1
    _w("failure_subtypes.csv",
       ["final_label", "raw_label", "error_type", "extraction_mode", "output_truncated",
        "count"],
       [{"final_label": k[0], "raw_label": k[1], "error_type": k[2],
         "extraction_mode": k[3], "output_truncated": k[4], "count": n}
        for k, n in sorted(fs.items(), key=lambda kv: -kv[1])])


def main():
    ap = argparse.ArgumentParser(description="Exp1 runner: build_model+solve, Layer 1 + Layer 2.")
    ap.add_argument("--problems", default=DEFAULT_PROBLEMS_PATH)
    ap.add_argument("--checkers", default=DEFAULT_CHECKERS_PATH)
    ap.add_argument("--audit-module", default=DEFAULT_AUDIT_PATH)
    ap.add_argument("--out", default=DEFAULT_OUTPUT_DIR)
    ap.add_argument("--provider", default=DEFAULT_PROVIDER, choices=["ollama", "openai"],
                    help="Model provider backend.")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--problem-ids", default="all", help="Comma-separated IDs or 'all'.")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    ap.add_argument("--request-timeout", type=int, default=180)
    ap.add_argument("--num-predict", type=int, default=12000,
                    help="Max generation tokens (raised from 6000: thinking models truncate code at low caps).")
    ap.add_argument("--exec-timeout", type=int, default=30)
    ap.add_argument("--audit-timeout", type=int, default=120)
    ap.add_argument("--write-details", action="store_true",
                    help="Also write checker_details.jsonl (noisy Layer-1 per-checker log).")
    ap.add_argument("--audit-even-if-objective-fails", action="store_true",
                    help="DEBUG ONLY: run Layer 2 formulation audit whenever code_ran & "
                         "schema_ok & has_build_model, even if objective_match is False. "
                         "Does NOT change scientific labels: silent_bug still requires "
                         "objective_match=True. Audit rows are recorded for inspection only.")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    audit_module_path = str(Path(args.audit_module).resolve())
    for sub in ["", "prompts", "responses", "generated_code", "execution_workdirs"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    problems = get_problems(load_json(args.problems))
    sel = parse_problem_ids(args.problem_ids)
    if sel is not None:
        problems = [p for p in problems if int(p["id"]) in sel]
    checkers_module = load_checkers_module(args.checkers)

    # Fail fast: every selected problem MUST have a checker registry entry. A missing entry
    # previously degraded to a 'registry_error' checker row that surfaced as failed_checks=None
    # and silently disabled Layer 1 for that problem. Stop loudly instead.
    # Resolve by ORIGINAL id (checker_key) so a renumbered subset validates against the
    # frozen registry rather than its new 1..N ids.
    missing_reg = [checker_key(p)[1] for p in problems
                   if checker_key(p)[0] not in getattr(checkers_module, "REGISTRY", {})]
    if missing_reg:
        raise RuntimeError(
            "checkers.REGISTRY is missing entries for ORIGINAL problem id(s): "
            f"{sorted(missing_reg)}. Ensure checkers.py (and any _checker_specs.json it reads) "
            "are present and importable next to it before running.")

    models = [m.strip() for m in args.models.split(",") if m.strip()]

    summary_rows, checker_detail_rows, audit_detail_rows = [], [], []

    # Live results.csv: every finished run row is appended and flushed to disk immediately,
    # so the file is inspectable mid-run and survives a crash. The end-of-run write_csv still
    # runs and produces the same file. record() is the single sink for finished rows; it both
    # keeps the in-memory list (for the analysis CSVs) and live-writes.
    _live_writer = LiveResultsWriter(out_dir / "results.csv")

    def record(row):
        summary_rows.append(row)
        _live_writer.append(row)

    for problem in problems:
        problem_id = int(problem["id"])                       # NEW id: labels run_ids/rows
        checker_pkey, original_problem_id = checker_key(problem)  # ORIGINAL id: checker/audit lookup
        data_instance = problem.get("data_instance", {})
        gold_answer = problem.get("answer")
        audit_specs = problem.get("formulation_audit_specs")
        for warn_key in ("GOLD_VALUE_WARNING", "GOLD_VALUE_STATUS"):
            if warn_key in problem:
                print(f"[{warn_key}] problem {problem_id}: {str(problem[warn_key])[:180]}...", file=sys.stderr)

        prompt = build_prompt(problem)
        prompt_hash = sha256_text(prompt)
        (out_dir / "prompts" / f"p{problem_id}_prompt.txt").write_text(prompt, encoding="utf-8")

        for model in models:
            safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
            for sample in range(args.samples):
                run_id = f"p{problem_id}__{safe_model}__s{sample}"
                print(f"Running {run_id}...")
                row = {"run_id": run_id, "model": model, "problem_id": problem_id,
                       "original_problem_id": original_problem_id, "sample": sample,
                       "prompt_hash": prompt_hash, "prompt_version": PROMPT_VERSION, "label": "not_run", "code_ran": False,
                       "schema_ok": False, "objective_match": False, "has_build_model": False,
                       "failed_checks": "", "failed_requirement_checks": "",
                       "formulation_violations": "", "flagged_formulation_violations": "",
                       "silent_bug_type": "", "silent_bug_requirements": "", "silent_bug_source": "none",
                       "raw_label": "", "final_label": "", "extraction_mode": "",
                       "total_requirement_count": "", "layer1_requirement_count": "",
                       "layer2_active_probe_count": "", "total_diagnostic_requirement_count": "",
                       "failed_requirement_check_count": 0, "formulation_violation_count": 0,
                       "total_violation_count": 0,
                       "audit_error": "", "error_type": "", "error_detail": ""}
                seed = args.seed + sample if args.seed is not None else None

                t0 = time.time()
                try:
                    if args.provider == "ollama":
                        response = call_ollama(model, prompt, args.ollama_url,
                                               args.temperature, seed, args.request_timeout,
                                               args.num_predict)
                    else:
                        response = call_openai(model, prompt,
                                               args.temperature, seed, args.request_timeout,
                                               args.num_predict)
                    response_time = time.time() - t0
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError, RuntimeError) as e:
                    failure_label = "ollama_failure" if args.provider == "ollama" else "openai_failure"
                    row.update({"label": failure_label, "error_type": failure_label,
                                "error_detail": f"{type(e).__name__}: {e}",
                                "response_time_sec": round(time.time() - t0, 3)})
                    record(row); continue
                except Exception as e:
                    failure_label = "ollama_failure" if args.provider == "ollama" else "openai_failure"
                    row.update({"label": failure_label, "error_type": failure_label,
                                "error_detail": f"{type(e).__name__}: {e}",
                                "response_time_sec": round(time.time() - t0, 3)})
                    record(row); continue

                raw_text = response.get("response", "")
                raw_path = out_dir / "responses" / f"{run_id}_raw.txt"
                raw_path.write_text(raw_text, encoding="utf-8")
                row["raw_response_path"] = str(raw_path)
                row["response_time_sec"] = round(response_time, 3)
                row["prompt_eval_count"] = response.get("prompt_eval_count", "")
                row["eval_count"] = response.get("eval_count", "")
                # Truncation detection: output hit the generation cap. Downstream failures for
                # this run are then interface artifacts (cut-off code), not model inability;
                # the flag lets analysis separate the two.
                try:
                    row["output_truncated"] = int(response.get("eval_count", 0)) >= args.num_predict
                except (TypeError, ValueError):
                    row["output_truncated"] = False
                # OpenAI reasoning models: the API explicitly reports status="incomplete"
                # with reason="max_output_tokens" when reasoning consumed the budget and the
                # visible answer was cut off (eval_count can sit just under the cap, so the
                # >= check above misses it). Treat that as truncation too.
                if response.get("openai_incomplete_reason") == "max_output_tokens":
                    row["output_truncated"] = True
                if row.get("openai_reasoning_tokens", response.get("openai_reasoning_tokens")):
                    row["reasoning_tokens"] = response.get("openai_reasoning_tokens", "")
                if row["output_truncated"]:
                    _rt = response.get("openai_reasoning_tokens", "")
                    _rt_note = f", reasoning_tokens={_rt}" if _rt != "" else ""
                    row["error_detail"] = (row.get("error_detail") or "") + \
                        f" [output truncated at num_predict cap ({args.num_predict}){_rt_note}; " \
                        f"raise --num-predict for reasoning models]"

                code, extraction_mode = extract_python_code_ex(raw_text)
                row["extraction_mode"] = extraction_mode
                code_path = out_dir / "generated_code" / f"{run_id}.py"
                code_path.write_text(code, encoding="utf-8")
                row["generated_code_path"] = str(code_path)

                work_dir = out_dir / "execution_workdirs" / run_id
                work_dir.mkdir(parents=True, exist_ok=True)
                result, failure_type, detail, has_build = run_generated_code(
                    code, data_instance, args.exec_timeout, work_dir)
                row["has_build_model"] = has_build

                if result is None:
                    label_for_failure = "contract_failure" if failure_type == "contract_failure" else "code_failure"
                    row.update({"label": label_for_failure, "error_type": failure_type, "error_detail": detail})
                    record(row); continue

                row["code_ran"] = True
                (work_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

                schema_ok, schema_errors = validate_solution_schema(result, problem["solution_schema"])
                row["schema_ok"] = schema_ok
                if not schema_ok:
                    row.update({"label": "schema_failure", "error_type": "schema_failure",
                                "error_detail": "; ".join(schema_errors)})
                    record(row); continue

                checker_data = dict(data_instance)
                # audit_data holds derived ground-truth structure (coverage, membership, etc.)
                # that is deliberately NOT shown to the tested model. Checkers/audit may use it.
                checker_data.update(problem.get("audit_data", {}))
                try:
                    checker_data["_gold_objective"] = float(gold_answer)
                except (TypeError, ValueError):
                    pass
                checker_rows = run_checkers(checkers_module, original_problem_id, checker_data, result)
                objective_match = infer_objective_match(checker_rows, result, gold_answer)
                label = classify(objective_match, checker_rows)

                # Research rule (unchanged): silent-bug labeling only matters when objective_match=True.
                # Debug rule: with --audit-even-if-objective-fails, run the audit whenever the
                # code ran, schema is valid, and build_model exists -- purely to inspect probe
                # behavior. It never flips a loud_bug into silent_bug.
                run_audit = bool(audit_specs) and (objective_match or args.audit_even_if_objective_fails)
                if run_audit and objective_match and not has_build:
                    # preserve existing behavior: objective matched but no build_model -> contract_failure
                    row["audit_error"] = "no build_model() exposed; Layer 2 skipped"
                    label = "contract_failure"
                elif run_audit and has_build:
                    if True:
                        audit_rows = None
                        audit_input_data = dict(data_instance)
                        audit_input_data.update(problem.get("audit_data", {}))
                        # Layer 2 needs the gold to run the objective_value probe on the
                        # canonical instance (mirrors checker_data at Layer 1). On perturbed
                        # instances gold is intentionally absent -> probe self-disables (UNKNOWN).
                        try:
                            audit_input_data["_gold_objective"] = float(gold_answer)
                        except (TypeError, ValueError):
                            pass
                        audit_rows, audit_err = run_formulation_audit_subprocess(
                            audit_input_data, audit_specs, audit_module_path, args.audit_timeout, work_dir)
                        if audit_rows is not None:
                            (work_dir / "formulation_audit.json").write_text(
                                json.dumps(audit_rows, indent=2), encoding="utf-8")
                            fviol = [r["requirement_id"] for r in audit_rows
                                     if r.get("status") == "FAIL" and not r.get("flagged", False)]
                            fflag = [r["requirement_id"] for r in audit_rows
                                     if r.get("status") == "FAIL" and r.get("flagged", False)]
                            funknown = [r for r in audit_rows
                                        if r.get("status") == "UNKNOWN" and not r.get("flagged", False)
                                        and r.get("probe_type") != "objective_value"]
                            row["formulation_violations"] = ",".join(map(str, fviol))
                            row["flagged_formulation_violations"] = ",".join(map(str, fflag))

                            # Label promotion is RESEARCH-only: requires objective_match=True.
                            # In debug mode (objective_match=False), record violations in the
                            # columns but do NOT change the loud/label classification.
                            # Unified silent-bug rule: an objective-correct run is a silent_bug if
                            # EITHER a Layer-1 requirement checker failed (already set by classify())
                            # OR Layer-2 found a formulation violation (fviol below). Layer 2 only
                            # ADDS to the label here; it never downgrades a Layer-1 silent_bug back
                            # to correct. funknown -> contract_failure only when not already silent.
                            if objective_match:
                                if fviol:
                                    label = "silent_bug"
                                elif funknown and label != "silent_bug":
                                    label = "contract_failure"
                                    row["audit_error"] = "; ".join(
                                        f"{r.get('requirement_id')}: {r.get('explanation')}"
                                        for r in funknown[:8]
                                    )
                            for ar in audit_rows:
                                audit_detail_rows.append({
                                    "run_id": run_id, "model": model, "problem_id": problem_id,
                                    "sample": sample, "requirement_id": ar.get("requirement_id"),
                                    "probe_type": ar.get("probe_type"), "status": ar.get("status"),
                                    "max_violation": ar.get("max_violation"), "witness": ar.get("witness"),
                                    "explanation": ar.get("explanation"), "flagged": ar.get("flagged", False),
                                    "raw": ar})
                        else:
                            row["audit_error"] = audit_err
                            if objective_match and label == "correct":
                                label = "audit_inconclusive"

                # Registry errors must never masquerade as a check id of None. If any appear,
                # this run's Layer 1 is invalid -> mark audit_inconclusive rather than correct.
                if any(r.get("checker_kind") == "registry_error" for r in checker_rows):
                    if label == "correct":
                        label = "audit_inconclusive"
                    row["audit_error"] = (row.get("audit_error") or "") + " checker registry error"
                failed_all = [r["checker_id"] for r in checker_rows
                              if r["status"] != "PASS" and r.get("checker_id") is not None]
                failed_reqs = [r["checker_id"] for r in checker_rows
                               if r["status"] != "PASS" and r.get("checker_kind") == "requirement"
                               and r.get("checker_id") is not None]

                # Silent-bug subtype: only meaningful for silent_bug rows; blank otherwise.
                # Uses the same broad definition already applied above (Layer-1 requirement
                # failure OR Layer-2 formulation violation on an objective-correct run).
                # Requirement-count columns: attached to EVERY row (incl. correct) so
                # silent-bug rate can be regressed against diagnostic surface later.
                row.update(requirement_count_columns(problem, checkers_module))
                _n_freq = len([r for r in checker_rows
                               if r["status"] != "PASS"
                               and r.get("checker_kind") == "requirement"
                               and not r.get("flagged", False)])
                _fv = row.get("formulation_violations", "")
                _n_fviol = len(_fv.split(",")) if _fv else 0
                row["failed_requirement_check_count"] = _n_freq
                row["formulation_violation_count"] = _n_fviol
                row["total_violation_count"] = _n_freq + _n_fviol
                row["silent_bug_source"] = silent_bug_source(_n_freq, _n_fviol) \
                    if label == "silent_bug" else "none"

                row["silent_bug_type"] = ""
                row["silent_bug_requirements"] = ""
                row["report_categories"] = ""
                if label == "silent_bug":
                    failed_req_rows = [r for r in checker_rows
                                       if r["status"] != "PASS"
                                       and r.get("checker_kind") == "requirement"
                                       and not r.get("flagged", False)]
                    fviol_ids = row.get("formulation_violations", "")
                    fviol_ids = fviol_ids.split(",") if fviol_ids else []
                    sbt, sbr = silent_bug_type(failed_req_rows, fviol_ids, problem)
                    row["silent_bug_type"] = sbt
                    row["silent_bug_requirements"] = sbr
                    # General-mechanism 7-category taxonomy (constraint_omission,
                    # constraint_misspecification, domain_or_bound_error, linking_or_logic_error,
                    # objective_accounting_error, over_restrictive_constraint, mixed_or_unclear).
                    # Emitted at source so results.csv carries it, not only the analyzer.
                    # Uses the audit bug_type (direction) when present for the omission/
                    # misspecification/over-restrictive split; falls back to category family.
                    try:
                        canon = build_requirement_resolver(problem)
                        cat_by = {r["requirement_id"]: r.get("category", "")
                                  for r in problem.get("requirements", [])}
                        # audit direction per requirement, if Layer 2 ran this row
                        dir_by = {}
                        _audit_rows_local = locals().get("audit_rows", None)
                        for ar in (_audit_rows_local or []):
                            bt = ar.get("bug_type") or ""
                            rr = canon(ar.get("requirement_id"))
                            if "too_loose" in bt or "not_enforced" in bt:
                                dir_by[rr] = ("model_accepts_forbidden",
                                              ar.get("max_violation") not in (None, float("inf")))
                            elif "too_tight" in bt or "over" in bt:
                                dir_by[rr] = ("model_rejects_feasible", None)
                        rcats = set()
                        seen_reqs = set()
                        for rr in failed_req_rows:
                            rid = canon(rr.get("requirement_id"))
                            seen_reqs.add(rid)
                        for rid in fviol_ids:
                            seen_reqs.add(canon(rid))
                        for rid in seen_reqs:
                            cat = cat_by.get(rid, "")
                            direction, wb = dir_by.get(rid, (None, None))
                            rcats.add(_report_category(cat, direction, wb))
                        row["report_categories"] = ";".join(sorted(rcats))
                    except Exception:
                        row["report_categories"] = ""

                recovery_modes = {"recovered_unclosed_fence", "recovered_split_blocks",
                                  "recovered_prose_slice", "recovered_prose_slice_recompiled",
                                  "recovered_prose_slice_trimmed"}
                raw_label = ("contract_failure"
                             if row.get("extraction_mode") in recovery_modes else label)
                row.update({"label": label, "final_label": label, "raw_label": raw_label,
                            "objective_match": objective_match,
                            "failed_checks": ",".join(map(str, failed_all)),
                            "failed_requirement_checks": ",".join(map(str, failed_reqs))})
                record(row)

                for cr in checker_rows:
                    d = {"run_id": run_id, "model": model, "problem_id": problem_id, "sample": sample}
                    d.update({"requirement_id": cr.get("requirement_id"), "checker_id": cr.get("checker_id"),
                              "checker_function": cr.get("checker_function"), "checker_kind": cr.get("checker_kind"),
                              "checker_status": cr.get("status"), "checker_detail": cr.get("detail")})
                    checker_detail_rows.append(d)

    _live_writer.close()
    write_csv(out_dir / "results.csv", summary_rows)
    write_jsonl(out_dir / "results.jsonl", summary_rows)
    write_analysis_outputs(out_dir, summary_rows,
                           {p["id"]: p for p in problems}, checkers_module)
    write_jsonl(out_dir / "formulation_audit_details.jsonl", audit_detail_rows)
    if args.write_details:
        write_jsonl(out_dir / "checker_details.jsonl", checker_detail_rows)
    print(f"\nDone. Results in: {out_dir}")
    print(f"  results.csv / results.jsonl")
    print(f"  formulation_audit_details.jsonl ({len(audit_detail_rows)} rows)")
    if args.write_details:
        print(f"  checker_details.jsonl ({len(checker_detail_rows)} rows)")


if __name__ == "__main__":
    main()