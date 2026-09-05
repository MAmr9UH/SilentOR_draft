import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    courses = data.get("courses", [])
    m = gp.Model()

    # Decision variables: 1 if course is taken
    sel_calculus = m.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = m.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = m.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_ms = m.addVar(vtype=GRB.BINARY, name="sel_ms")
    sel_cs = m.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = m.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = m.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Time slots for prerequisites (1..N)
    N = max(7, len(courses))
    t_calculus = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_calculus")
    t_or = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_or")
    t_ds = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_ds")
    t_ms = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_ms")
    t_cs = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_cs")
    t_cp = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_cp")
    t_fc = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name="t_fc")

    m.update()

    M = 100  # big-M

    # Precedence constraints (active when course is selected)
    m.addConstr(t_cp <= t_cs - 1 + M*(1 - sel_cs))
    m.addConstr(t_cp <= t_ds - 1 + M*(1 - sel_ds))
    m.addConstr(t_calculus <= t_ms - 1 + M*(1 - sel_ms))
    m.addConstr(t_ms <= t_fc - 1 + M*(1 - sel_fc))

    # Selection implies prerequisites
    m.addConstr(sel_ms <= sel_calculus)
    m.addConstr(sel_fc <= sel_ms)
    m.addConstr(sel_cs <= sel_cp)
    m.addConstr(sel_ds <= sel_cp)

    # Category counts (at least 2 per category; overlapping counts allowed)
    m.addConstr(gp.quicksum([sel_calculus, sel_or, sel_ds, sel_ms, sel_fc]) >= 2)  # Math
    m.addConstr(gp.quicksum([sel_or, sel_ms, sel_cs, sel_fc]) >= 2)              # OR
    m.addConstr(gp.quicksum([sel_ds, sel_cs, sel_cp]) >= 2)                       # Computer

    # Objective: minimize total courses taken
    m.setObjective(gp.quicksum([sel_calculus, sel_or, sel_ds, sel_ms, sel_cs, sel_cp, sel_fc]), GRB.MINIMIZE)

    m.update()

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_ms": sel_ms,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    return m, variables

def solve(data: dict) -> dict:
    from math import isnan
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = model.ObjVal

    solution = {}
    for key in ["sel_calculus", "sel_or", "sel_ds", "sel_ms", "sel_cs", "sel_cp", "sel_fc"]:
        var = variables[key]
        val = var.X
        solution[key] = int(round(val))

    return {
        "status": status,
        "objective": float(objective) if not isnan(objective) else None,
        "solution": {
            "sel_calculus": solution["sel_calculus"],
            "sel_or": solution["sel_or"],
            "sel_ds": solution["sel_ds"],
            "sel_ms": solution["sel_ms"],
            "sel_cs": solution["sel_cs"],
            "sel_cp": solution["sel_cp"],
            "sel_fc": solution["sel_fc"]
        }
    }