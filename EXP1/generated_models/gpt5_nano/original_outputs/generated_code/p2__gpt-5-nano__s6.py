import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("course_selection_min")
    
    # Decision variables: binary selection for each course
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_ms = model.addVar(vtype=GRB.BINARY, name="sel_ms")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")
    
    # Time variables for precedence constraints
    t_calculus = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_calculus")
    t_or = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_or")
    t_ds = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_ds")
    t_ms = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_ms")
    t_cs = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_cs")
    t_cp = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_cp")
    t_fc = model.addVar(vtype=GRB.INTEGER, lb=1, ub=4, name="t_fc")
    
    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_ms": sel_ms,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }
    
    # Objective: minimize total number of courses taken
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_ms + sel_cs + sel_cp + sel_fc, GRB.MINIMIZE)
    
    # Category constraints (exactly 2 per category)
    # Math category: calculus, or, ds, ms, fc
    model.addConstr(sel_calculus + sel_or + sel_ds + sel_ms + sel_fc == 2, name="math_count")
    # Operations Research category: or, ms, cs, fc
    model.addConstr(sel_or + sel_ms + sel_cs + sel_fc == 2, name="or_count")
    # Computer category: ds, cs, cp
    model.addConstr(sel_ds + sel_cs + sel_cp == 2, name="computer_count")
    
    # Prerequisite implications:
    # cs and ds require cp
    model.addConstr(sel_cs <= sel_cp, name="cs_requires_cp")
    model.addConstr(sel_ds <= sel_cp, name="ds_requires_cp")
    # ms requires calculus
    model.addConstr(sel_ms <= sel_calculus, name="ms_requires_calculus")
    # fc requires ms
    model.addConstr(sel_fc <= sel_ms, name="fc_requires_ms")
    
    # Prerequisite time restrictions with Big-M
    M = 10  # large enough given time horizon 1..4
    model.addConstr(t_cs >= t_cp + 1 - M * (1 - sel_cs), name="time_cs")
    model.addConstr(t_ds >= t_cp + 1 - M * (1 - sel_ds), name="time_ds")
    model.addConstr(t_ms >= t_calculus + 1 - M * (1 - sel_ms), name="time_ms")
    model.addConstr(t_fc >= t_ms + 1 - M * (1 - sel_fc), name="time_fc")
    
    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Status mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status_str = status_map.get(status_code, str(status_code))
    
    # Read objective value
    objective_val = float(model.ObjVal) if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INFEASIBLE, GRB.UNBOUNDED, GRB.INF_OR_UNBD) else float(model.ObjVal)
    
    # Ensure variable values are updated before reading
    model.update()
    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_ms": int(variables["sel_ms"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X)
    }
    
    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }