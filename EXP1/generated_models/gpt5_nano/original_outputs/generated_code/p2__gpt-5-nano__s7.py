import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    courses = data.get("courses", [])
    n = len(courses)

    # Decision variables: binary selection indicators
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_ms = model.addVar(vtype=GRB.BINARY, name="sel_ms")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Time/order variables for prerequisites (integer with domain 0..n-1)
    t_calculus = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_calculus")
    t_or = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_or")
    t_ds = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_ds")
    t_ms = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_ms")
    t_cs = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_cs")
    t_cp = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_cp")
    t_fc = model.addVar(vtype=GRB.INTEGER, lb=0, ub=n-1, name="t_fc")

    model.update()

    M = max(1, n)  # Big-M constant; ensures cross constraints activate only when the target is selected

    # Category quotas (minimum counts)
    math_count = sel_calculus + sel_or + sel_ds + sel_ms + sel_fc
    or_count = sel_or + sel_ms + sel_cs + sel_fc
    computer_count = sel_ds + sel_cs + sel_cp

    model.addConstr(math_count >= 2, name="math_count_ge_2")
    model.addConstr(or_count >= 2, name="or_count_ge_2")
    model.addConstr(computer_count >= 2, name="computer_count_ge_2")

    # Precedence due to prerequisites
    model.addConstr(sel_ds <= sel_cp)  # ds after cp
    model.addConstr(sel_cs <= sel_cp)  # cs after cp

    # fc must be after ms; ms after calculus
    model.addConstr(sel_ms <= sel_calculus)  # ms after calculus (causes calculus if ms is chosen)
    model.addConstr(sel_fc <= sel_ms)        # fc after ms

    # Time constraints to enforce ordering when courses are selected
    model.addConstr(t_ms >= t_calculus + 1 - M * (1 - sel_ms))
    model.addConstr(t_fc >= t_ms       + 1 - M * (1 - sel_fc))
    model.addConstr(t_ds >= t_cp       + 1 - M * (1 - sel_ds))
    model.addConstr(t_cs >= t_cp       + 1 - M * (1 - sel_cs))

    # Objective: minimize total number of courses selected
    objective = (sel_calculus + sel_or + sel_ds + sel_ms + sel_cs + sel_cp + sel_fc)
    model.setObjective(objective, GRB.MINIMIZE)

    model.update()

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_ms": sel_ms,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string for the output
    if model.Status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif model.Status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif model.Status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif model.Status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif model.Status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(model.Status)

    # Read objective value
    objective_value = float(model.ObjVal)

    # Read solution values for the required variables
    solution_vals = {}
    for key, var in variables.items():
        try:
            solution_vals[key] = int(round(var.X))
        except Exception:
            solution_vals[key] = 0

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution_vals
    }