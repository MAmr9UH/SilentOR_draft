import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Decision variables: integers >= 0 representing number of workers on each shift
    s1 = model.addVar(vtype=GRB.INTEGER, name="s1", lb=0)
    s2 = model.addVar(vtype=GRB.INTEGER, name="s2", lb=0)
    s3 = model.addVar(vtype=GRB.INTEGER, name="s3", lb=0)
    s4 = model.addVar(vtype=GRB.INTEGER, name="s4", lb=0)
    model.update()
    
    required = data["workers_required_by_window"]  # length 8
    cover = data["shift_coverage"]                 # keys "1","2","3","4" -> lists of windows
    wage = data["shift_wage"]                      # keys "1","2","3","4" -> per-shift wage
    
    # Constraints: for each window w, sum of covering shifts' workers >= required
    for w in range(8):
        expr = 0
        if w in cover.get("1", []):
            expr += s1
        if w in cover.get("2", []):
            expr += s2
        if w in cover.get("3", []):
            expr += s3
        if w in cover.get("4", []):
            expr += s4
        model.addConstr(expr >= required[w], name=f"cover_w{w}")
    
    # Objective: minimize total wage cost
    obj = s1 * wage.get("1", 0) + s2 * wage.get("2", 0) + s3 * wage.get("3", 0) + s4 * wage.get("4", 0)
    model.setObjective(obj, GRB.MINIMIZE)
    
    return model, {"s1": s1, "s2": s2, "s3": s3, "s4": s4}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()
    
    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)
    
    solution = {
        "s1": int(variables["s1"].X),
        "s2": int(variables["s2"].X),
        "s3": int(variables["s3"].X),
        "s4": int(variables["s4"].X)
    }
    
    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }