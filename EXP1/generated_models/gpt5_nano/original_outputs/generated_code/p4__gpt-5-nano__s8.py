import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.Params.OutputFlag = 0

    foods = data["foods"]

    # Decision variables: quantity of each food, continuous and non-negative
    variables = {}
    for f in foods:
        variables[f] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"qty_{f}")

    model.update()

    # Objective: minimize total cost
    model.setObjective(gp.quicksum(data["cost"][f] * variables[f] for f in foods), GRB.MINIMIZE)

    # Nutritional constraints (at least minimum targets)
    min_protein = data["min"]["protein"]
    min_carbs = data["min"]["carb"]
    min_calories = data["min"]["calories"]

    model.addConstr(gp.quicksum(data["protein"][f] * variables[f] for f in foods) >= min_protein, name="min_protein")
    model.addConstr(gp.quicksum(data["carb"][f] * variables[f] for f in foods) >= min_carbs, name="min_carbs")
    model.addConstr(gp.quicksum(data["calories"][f] * variables[f] for f in foods) >= min_calories, name="min_calories")

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

    objective_value = float(model.ObjVal)

    solution = {
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X),
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }