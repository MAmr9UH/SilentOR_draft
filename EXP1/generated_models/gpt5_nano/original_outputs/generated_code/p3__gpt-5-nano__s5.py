import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Decision variables: number of salespeople starting at each hour
    s2  = model.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s6  = model.addVar(vtype=GRB.INTEGER, lb=0, name="s6")
    s10 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s10")
    s14 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s14")
    s18 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s18")
    s22 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s22")
    
    variables = {
        "s2": s2,
        "s6": s6,
        "s10": s10,
        "s14": s14,
        "s18": s18,
        "s22": s22
    }
    
    # Objective: minimize total number of salespeople starting
    model.setObjective(s2 + s6 + s10 + s14 + s18 + s22, GRB.MINIMIZE)
    
    # Demand constraints by period start
    demand = data.get("demand_by_period_start", {})
    model.addConstr(s2  + s22 >= int(demand.get("2", 0)),  name="c_2")
    model.addConstr(s2  + s6  >= int(demand.get("6", 0)),  name="c_6")
    model.addConstr(s6  + s10 >= int(demand.get("10", 0)), name="c_10")
    model.addConstr(s10 + s14 >= int(demand.get("14", 0)), name="c_14")
    model.addConstr(s14 + s18 >= int(demand.get("18", 0)), name="c_18")
    model.addConstr(s18 + s22 >= int(demand.get("22", 0)), name="c_22")
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status = model.Status
    status_str_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_str_map.get(status, str(status))
    
    objective = float(model.ObjVal) if model.ObjVal is not None else None
    
    solution = {k: float(v.X) for k, v in variables.items()}
    
    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }