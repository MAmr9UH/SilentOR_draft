import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    foods = data["foods"]

    # Decision variables: quantity of each food
    variables = {}
    for f in foods:
        variables[f] = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name=f"qty_{f}")

    model.update()

    # Objective: minimize total cost
    model.setObjective(gp.quicksum(data["cost"][f] * variables[f] for f in foods), GRB.MINIMIZE)

    # Constraints: meet or exceed nutritional minimums
    model.addConstr(gp.quicksum(data["protein"][f] * variables[f] for f in foods) >= data["min"]["protein"], name="ProteinMin")
    model.addConstr(gp.quicksum(data["carb"][f] * variables[f] for f in foods) >= data["min"]["carb"], name="CarbMin")
    model.addConstr(gp.quicksum(data["calories"][f] * variables[f] for f in foods) >= data["min"]["calories"], name="CalMin")

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

    solution = {
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X)
    }

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }