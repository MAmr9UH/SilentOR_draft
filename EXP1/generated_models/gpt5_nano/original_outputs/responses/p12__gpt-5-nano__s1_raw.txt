import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening = data["fixed_opening_cost"]
    transport = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]
    
    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
    
    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")
    
    model.update()
    
    # Objective: minimize opening costs + transportation costs
    obj = gp.LinExpr()
    for c in centers:
        obj += fixed_opening[c] * y[c]
        for s in stores:
            obj += transport[c][s] * f[c][s]
    model.setObjective(obj, GRB.MINIMIZE)
    
    # Constraints
    # Demand satisfaction
    for s in stores:
        model.addConstr(quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")
    
    # Center capacity linked to opening decision
    for c in centers:
        model.addConstr(quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")
    
    # Prepare variables dict with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]
    
    return model, variables

def solve(data: dict) -> dict:
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
    objective = float(model.ObjVal)
    
    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = variables[f"y_{c}"].X
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = variables[f"f_{c}_{s}"].X
    
    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }