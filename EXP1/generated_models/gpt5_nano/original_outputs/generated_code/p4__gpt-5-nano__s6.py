import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    foods = data["foods"]

    # Create decision variables (continuous, >= 0)
    variables = {}
    for f in foods:
        variables[f] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f)

    model.update()

    # Constraints: meet nutritional minimums
    protein_min = data["min"]["protein"]
    carb_min = data["min"]["carb"]
    cal_min = data["min"]["calories"]

    model.addConstr(gp.quicksum(data["protein"][f] * variables[f] for f in foods) >= protein_min, name="protein")
    model.addConstr(gp.quicksum(data["carb"][f] * variables[f] for f in foods) >= carb_min, name="carb")
    model.addConstr(gp.quicksum(data["calories"][f] * variables[f] for f in foods) >= cal_min, name="calories")

    # Objective: minimize cost
    model.setObjective(gp.quicksum(data["cost"][f] * variables[f] for f in foods), sense=GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_str = "UNKNOWN"
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"

    objective = float(model.ObjVal)

    solution = {
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }