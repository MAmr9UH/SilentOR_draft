import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    foods = data["foods"]
    
    # Decision variables: quantity of each food to include
    vars_by_food = {}
    for f in foods:
        vars_by_food[f] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f)
    model.update()
    
    # Objective: minimize total cost
    total_cost = gp.quicksum(data["cost"][f] * vars_by_food[f] for f in foods)
    model.setObjective(total_cost, GRB.MINIMIZE)
    
    # Nutritional constraints (at least target amounts)
    min_protein = data["min"]["protein"]
    min_carb = data["min"]["carb"]
    min_cal = data["min"]["calories"]
    
    model.addConstr(gp.quicksum(data["protein"][f] * vars_by_food[f] for f in foods) >= min_protein, name="protein_min")
    model.addConstr(gp.quicksum(data["carb"][f] * vars_by_food[f] for f in foods) >= min_carb, name="carb_min")
    model.addConstr(gp.quicksum(data["calories"][f] * vars_by_food[f] for f in foods) >= min_cal, name="cal_min")
    
    # Return the model and a flat dict of variables with exact keys
    variables = {
        "chicken": vars_by_food["chicken"],
        "rice": vars_by_food["rice"],
        "broccoli": vars_by_food["broccoli"],
        "tofu": vars_by_food["tofu"],
        "beans": vars_by_food["beans"]
    }
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
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
    
    model.update()
    objective_value = float(model.ObjVal) if model.ObjVal is not None else None
    
    solution = {
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X)
    }
    
    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }