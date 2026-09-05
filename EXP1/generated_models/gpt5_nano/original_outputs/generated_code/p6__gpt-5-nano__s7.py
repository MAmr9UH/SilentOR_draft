from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    regions = [1, 2, 3, 4, 5]
    move_cost = data["move_cost"]

    model = Model()
    # Decision variables: x_i_j for i != j
    variables = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            var_name = f"x_{i}_{j}"
            variables[var_name] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=var_name)

    model.update()

    # Objective: minimize total transportation cost
    obj = quicksum(move_cost[f"{i}_{j}"] * variables[f"x_{i}_{j}"]
                   for i in regions for j in regions if i != j)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints: final cars per region >= cars_needed
    current_cars = data["current_cars"]
    cars_needed = data["cars_needed"]
    for r in regions:
        inflow = quicksum(variables[f"x_{k}_{r}"] for k in regions if k != r)
        outflow = quicksum(variables[f"x_{r}_{k}"] for k in regions if k != r)
        rhs = cars_needed[str(r)] - current_cars[str(r)]
        model.addConstr(inflow - outflow >= rhs, name=f"balance_{r}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a readable string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = float(model.ObjVal)

    # Ensure latest variable values are available
    model.update()

    # Prepare solution dictionary with exact keys and numeric values
    keys_order = [
        "x_1_2", "x_1_3", "x_1_4", "x_1_5",
        "x_2_1", "x_2_3", "x_2_4", "x_2_5",
        "x_3_1", "x_3_2", "x_3_4", "x_3_5",
        "x_4_1", "x_4_2", "x_4_3", "x_4_5",
        "x_5_1", "x_5_2", "x_5_3", "x_5_4"
    ]
    solution = {key: float(variables[key].X) for key in keys_order}

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }