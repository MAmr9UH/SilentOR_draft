def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("nutrition")

    # Define variables for the five foods (continuous, >= 0)
    var_keys = ["chicken", "rice", "broccoli", "tofu", "beans"]
    variables = {}
    for k in var_keys:
        variables[k] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"{k}")

    model.update()

    # Objective: minimize total cost
    cost = data["cost"]
    model.setObjective(gp.quicksum(cost[k] * variables[k] for k in var_keys), GRB.MINIMIZE)

    # Nutritional constraints: at least the minimums
    minreq = data["min"]
    protein = data["protein"]
    carb = data["carb"]
    calories = data["calories"]

    model.addConstr(gp.quicksum(protein[k] * variables[k] for k in var_keys) >= minreq["protein"], name="protein_min")
    model.addConstr(gp.quicksum(carb[k] * variables[k] for k in var_keys) >= minreq["carb"], name="carb_min")
    model.addConstr(gp.quicksum(calories[k] * variables[k] for k in var_keys) >= minreq["calories"], name="cal_min")

    return model, variables


def solve(data: dict) -> dict:
    # Build and optimize the model
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    from gurobipy import GRB
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    # Extract solution values for each variable
    solution = {
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X)
    }

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }