import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Decision variables: number starting at each hour
    s2 = model.addVar(vtype=GRB.INTEGER, name="s2", lb=0)
    s6 = model.addVar(vtype=GRB.INTEGER, name="s6", lb=0)
    s10 = model.addVar(vtype=GRB.INTEGER, name="s10", lb=0)
    s14 = model.addVar(vtype=GRB.INTEGER, name="s14", lb=0)
    s18 = model.addVar(vtype=GRB.INTEGER, name="s18", lb=0)
    s22 = model.addVar(vtype=GRB.INTEGER, name="s22", lb=0)
    
    # Objective: minimize total number of salespeople
    model.setObjective(s2 + s6 + s10 + s14 + s18 + s22, GRB.MINIMIZE)
    
    # Demands by period (convert keys to int)
    demands = {}
    for k, v in data.get("demand_by_period_start", {}).items():
        try:
            demands[int(k)] = v
        except Exception:
            pass
    
    # Coverage constraints
    model.addConstr(s2 + s22 >= demands.get(2, 0))     # 2:00-6:00
    model.addConstr(s2 + s6 >= demands.get(6, 0))      # 6:00-10:00
    model.addConstr(s6 + s10 >= demands.get(10, 0))    # 10:00-14:00
    model.addConstr(s10 + s14 >= demands.get(14, 0))   # 14:00-18:00
    model.addConstr(s14 + s18 >= demands.get(18, 0))   # 18:00-22:00
    model.addConstr(s18 + s22 >= demands.get(22, 0))   # 22:00-2:00
    
    variables = {
        "s2": s2,
        "s6": s6,
        "s10": s10,
        "s14": s14,
        "s18": s18,
        "s22": s22
    }
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_int = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_int, str(status_int))
    
    obj_val = model.ObjVal
    # Ensure variable values are read after optimization
    model.update()
    solution_vals = {
        "s2": int(variables["s2"].X),
        "s6": int(variables["s6"].X),
        "s10": int(variables["s10"].X),
        "s14": int(variables["s14"].X),
        "s18": int(variables["s18"].X),
        "s22": int(variables["s22"].X)
    }
    
    return {
        "type": "object",
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution_vals
    }