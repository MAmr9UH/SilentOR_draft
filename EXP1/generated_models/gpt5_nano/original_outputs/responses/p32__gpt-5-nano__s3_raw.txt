import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("flowshop_permutation")
    
    batches = data["batches"]
    vats = data["vats"]
    positions = data["positions"]
    
    # Build processing times t[(b, v)]
    t = {}
    for b in batches:
        times_b = data["processing_time"][str(b)]
        for v in vats:
            t[(b, v)] = float(times_b[str(v)])
    
    # Decision variables: y[b,p] (binary), C[p,v] (continuous), Cmax (continuous)
    y = {}
    for b in batches:
        for p in positions:
            y[(b, p)] = model.addVar(vtype=GRB.BINARY, name=f"y_{b}_{p}")
    
    C = {}
    for p in positions:
        for v in vats:
            C[(p, v)] = model.addVar(vtype=GRB.CONTINUOUS, name=f"C_{p}_{v}")
    
    Cmax = model.addVar(vtype=GRB.CONTINUOUS, name="Cmax")
    
    model.update()
    
    # Constraints
    # 1) Each batch assigned to exactly one position
    for b in batches:
        model.addConstr(gp.quicksum(y[(b, p)] for p in positions) == 1, name=f"OnePos_batch_{b}")
    
    # 2) Each position has exactly one batch
    for p in positions:
        model.addConstr(gp.quicksum(y[(b, p)] for b in batches) == 1, name=f"OneBatch_pos_{p}")
    
    # 3) C_1_v = sum_b y[b,1] * t[b,v]
    for v in vats:
        model.addConstr(C[(1, v)] == gp.quicksum(y[(b, 1)] * t[(b, v)] for b in batches))
    
    # 4) C_p_v = C_(p-1)_v + sum_b y[b,p] * t[b,v], for p=2..5
    for p in positions[1:]:
        for v in vats:
            model.addConstr(C[(p, v)] == C[(p - 1, v)] + gp.quicksum(y[(b, p)] * t[(b, v)] for b in batches))
    
    # 5) Cmax >= C_p_v for all p,v
    for p in positions:
        for v in vats:
            model.addConstr(Cmax >= C[(p, v)])
    
    # Objective: minimize makespan
    model.setObjective(Cmax, GRB.MINIMIZE)
    
    # Collect variables into the required dictionary with exact keys
    variables = {}
    for b in batches:
        for p in positions:
            variables[f"y_{b}_{p}"] = y[(b, p)]
    for p in positions:
        for v in vats:
            variables[f"C_{p}_{v}"] = C[(p, v)]
    variables["Cmax"] = Cmax
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Map status to string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)
    
    model.update()
    objective = float(model.ObjVal)
    
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)
    
    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }