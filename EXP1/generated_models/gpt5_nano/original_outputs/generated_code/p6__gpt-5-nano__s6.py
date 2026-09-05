import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    regions = data["regions"]

    # Create decision variables for all i != j
    variables = {}
    for i in regions:
        for j in regions:
            if i != j:
                key = f"x_{i}_{j}"
                v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
                variables[key] = v

    # Objective: minimize total moving cost
    objective = gp.quicksum(
        data["move_cost"][f"{i}_{j}"] * variables[f"x_{i}_{j}"]
        for i in regions for j in regions if i != j
    )
    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints: for each region k, current + inflow - outflow >= needed
    for k in regions:
        current = data["current_cars"][str(k)]
        need = data["cars_needed"][str(k)]
        inflow = gp.quicksum(variables[f"x_{i}_{k}"] for i in regions if i != k)
        outflow = gp.quicksum(variables[f"x_{k}_{j}"] for j in regions if j != k)
        model.addConstr(current + inflow - outflow >= need, name=f"balance_{k}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_int)

    objective = model.ObjVal

    solution_keys_order = [
        "x_1_2","x_1_3","x_1_4","x_1_5",
        "x_2_1","x_2_3","x_2_4","x_2_5",
        "x_3_1","x_3_2","x_3_4","x_3_5",
        "x_4_1","x_4_2","x_4_3","x_4_5",
        "x_5_1","x_5_2","x_5_3","x_5_4"
    ]
    solution = {key: int(round(variables[key].X)) for key in solution_keys_order}

    return {
        "status": status,
        "objective": int(round(objective)),
        "solution": solution
    }