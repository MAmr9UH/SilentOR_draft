import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    foods = data["foods"]
    protein = data["protein"]
    carb = data["carb"]
    calories = data["calories"]
    cost = data["cost"]
    mins = data["min"]

    model = gp.Model("nutrition_min_cost")

    # Decision variables: quantity of each food
    x = {}
    for f in foods:
        x[f] = model.addVar(lb=0.0, name=f)

    model.update()

    # Nutritional constraints (at least targets)
    model.addConstr(gp.quicksum(protein[f] * x[f] for f in foods) >= mins["protein"], name="protein_min")
    model.addConstr(gp.quicksum(carb[f] * x[f] for f in foods) >= mins["carb"], name="carb_min")
    model.addConstr(gp.quicksum(calories[f] * x[f] for f in foods) >= mins["calories"], name="cal_min")

    # Objective: minimize cost
    model.setObjective(gp.quicksum(cost[f] * x[f] for f in foods), GRB.MINIMIZE)

    # Return variables with exactly the required keys
    variables = {
        "chicken": x["chicken"],
        "rice": x["rice"],
        "broccoli": x["broccoli"],
        "tofu": x["tofu"],
        "beans": x["beans"],
    }

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
    status_str = status_map.get(model.Status, str(model.Status))

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