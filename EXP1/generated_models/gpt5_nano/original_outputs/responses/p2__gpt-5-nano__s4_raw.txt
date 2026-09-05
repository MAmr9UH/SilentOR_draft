import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    codes = data.get("courses", [])
    if not codes:
        codes = ["calculus","or","ds","ms","cs","cp","fc"]
    T = max(1, len(codes))
    m = gp.Model()

    # Create binary selection variables by course code
    code_to_var = {}
    for code in codes:
        code_to_var[code] = m.addVar(vtype=GRB.BINARY, name=f"sel_{code}")

    # Create time/order variables for precedence constraints
    time_vars = {}
    for code in codes:
        time_vars[code] = m.addVar(vtype=GRB.INTEGER, lb=0, ub=T-1, name=f"t_{code}")

    m.update()

    # Problem-specific category mapping (derived from the statement)
    category_map = {
        "calculus": ["math"],
        "or": ["math", "or"],
        "ds": ["math", "computer"],
        "ms": ["math", "or"],
        "cs": ["computer", "or"],
        "cp": ["computer"],
        "fc": ["math", "or"]
    }

    # Build category constraint sets (counting multis)
    math_codes = [c for c in codes if "math" in category_map.get(c, [])]
    or_codes = [c for c in codes if "or" in category_map.get(c, [])]
    comp_codes = [c for c in codes if "computer" in category_map.get(c, [])]

    m.addConstr(gp.quicksum(code_to_var[c] for c in math_codes) >= 2, name="math2")
    m.addConstr(gp.quicksum(code_to_var[c] for c in or_codes) >= 2, name="or2")
    m.addConstr(gp.quicksum(code_to_var[c] for c in comp_codes) >= 2, name="comp2")

    # Prerequisite implications (selection)
    # ds and cs require cp
    m.addConstr(code_to_var["ds"] <= code_to_var["cp"])
    m.addConstr(code_to_var["cs"] <= code_to_var["cp"])
    # ms requires calculus
    m.addConstr(code_to_var["ms"] <= code_to_var["calculus"])
    # fc requires ms
    m.addConstr(code_to_var["fc"] <= code_to_var["ms"])

    # Time precedence (if taken, must respect prereq)
    M = T  # big-M

    m.addConstr(time_vars["ds"] >= time_vars["cp"] + 1 - M * (1 - code_to_var["ds"]))
    m.addConstr(time_vars["cs"] >= time_vars["cp"] + 1 - M * (1 - code_to_var["cs"]))
    m.addConstr(time_vars["ms"] >= time_vars["calculus"] + 1 - M * (1 - code_to_var["ms"]))
    m.addConstr(time_vars["fc"] >= time_vars["ms"] + 1 - M * (1 - code_to_var["fc"]))

    # Objective: minimize total number of courses taken
    m.setObjective(
        gp.quicksum(code_to_var[c] for c in codes),
        GRB.MINIMIZE
    )

    # Prepare return dictionary with exactly the required keys
    variables = {
        "sel_calculus": code_to_var["calculus"],
        "sel_or": code_to_var["or"],
        "sel_ds": code_to_var["ds"],
        "sel_ms": code_to_var["ms"],
        "sel_cs": code_to_var["cs"],
        "sel_cp": code_to_var["cp"],
        "sel_fc": code_to_var["fc"],
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))

    # Objective value
    objective = float(model.ObjVal)

    # Ensure variables are updated before reading X
    model.update()
    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_ms": int(variables["sel_ms"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X),
    }

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }