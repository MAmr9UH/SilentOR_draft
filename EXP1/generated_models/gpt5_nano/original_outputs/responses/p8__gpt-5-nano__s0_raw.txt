import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Decision variables: integer number of workers on each shift
    s1 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s1")
    s2 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s3 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s3")
    s4 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s4")
    
    model.update()
    
    # Windows requirements
    required = data["workers_required_by_window"]  # length 8
    
    cov1 = data["shift_coverage"]["1"]  # windows covered by shift 1
    cov2 = data["shift_coverage"]["2"]  # windows covered by shift 2
    cov3 = data["shift_coverage"]["3"]  # windows covered by shift 3
    cov4 = data["shift_coverage"]["4"]  # windows covered by shift 4
    
    # Coverage constraints: for each window, sum of covering shifts >= required workers
    for w in range(8):
        expr = gp.LinExpr()
        if w in cov1:
            expr += s1
        if w in cov2:
            expr += s2
        if w in cov3:
            expr += s3
        if w in cov4:
            expr += s4
        model.addConstr(expr >= required[w])
    
    # Objective: minimize total wage cost
    wage = data["shift_wage"]
    obj = wage["1"] * s1 + wage["2"] * s2 + wage["3"] * s3 + wage["4"] * s4
    model.setObjective(obj, GRB.MINIMIZE)
    
    variables = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4
    }
    
    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Map status to string (as required by the schema)
    status_num = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.CUTOFF: "CUTOFF",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.NODE_DOWN: "NODE_DOWN",
    }
    status = status_map.get(status_num, str(status_num))
    
    objective = float(model.ObjVal) if model.ObjVal is not None else None
    
    s1_val = int(variables["s1"].X)
    s2_val = int(variables["s2"].X)
    s3_val = int(variables["s3"].X)
    s4_val = int(variables["s4"].X)
    
    solution = {
        "s1": s1_val,
        "s2": s2_val,
        "s3": s3_val,
        "s4": s4_val
    }
    
    result = {
        "status": status,
        "objective": objective,
        "solution": solution
    }
    return result