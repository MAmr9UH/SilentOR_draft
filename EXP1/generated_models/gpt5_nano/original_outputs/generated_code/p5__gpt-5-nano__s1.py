import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    # Create binary decision variables for each course
    sel_calculus = m.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = m.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = m.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_bs = m.addVar(vtype=GRB.BINARY, name="sel_bs")
    sel_cs = m.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = m.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = m.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Objective: minimize total number of courses taken
    m.setObjective(sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc, GRB.MINIMIZE)

    # Requirements
    # Math: at least 2 among calculus, or, ds, bs, fc
    m.addConstr(sel_calculus + sel_or + sel_ds + sel_bs + sel_fc >= 2, name="math_req")
    # OR: at least 2 among or, bs, cs, fc
    m.addConstr(sel_or + sel_bs + sel_cs + sel_fc >= 2, name="or_req")
    # Computer: at least 2 among ds, cs, cp
    m.addConstr(sel_ds + sel_cs + sel_cp >= 2, name="comp_req")

    # Prerequisites
    # bs -> calculus
    m.addConstr(sel_bs <= sel_calculus, name="bs_prereq_calculus")
    # fc -> bs
    m.addConstr(sel_fc <= sel_bs, name="fc_prereq_bs")
    # cs -> cp
    m.addConstr(sel_cs <= sel_cp, name="cs_prereq_cp")
    # ds -> cp
    m.addConstr(sel_ds <= sel_cp, name="ds_prereq_cp")

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_bs": sel_bs,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status_str = status_map.get(status_code, "UNKNOWN")

    # Read objective value
    try:
        objective_value = float(model.ObjVal)
    except Exception:
        objective_value = 0.0

    # Read solution values
    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_bs": int(variables["sel_bs"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X)
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }