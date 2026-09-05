import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model("car_relocation")

    regions = data["regions"]
    move_cost = data["move_cost"]
    current_cars = data["current_cars"]
    cars_needed = data["cars_needed"]

    variables = {}

    # Decision variables: x_i_j for i != j
    for i in regions:
        for j in regions:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            cost = move_cost[f"{i}_{j}"]
            var = model.addVar(lb=0.0, ub=gp.GRB.INFINITY, obj=cost, vtype=gp.GRB.CONTINUOUS, name=key)
            variables[key] = var

    model.update()

    # Constraints: final cars in region k >= cars_needed[k]
    for k in regions:
        sum_in = gp.quicksum(variables[f"x_{i}_{k}"] for i in regions if i != k)
        sum_out = gp.quicksum(variables[f"x_{k}_{j}"] for j in regions if j != k)
        model.addConstr(current_cars[str(k)] + sum_in - sum_out >= cars_needed[str(k)], name=f"need_{k}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal)

    order = [
        "x_1_2","x_1_3","x_1_4","x_1_5",
        "x_2_1","x_2_3","x_2_4","x_2_5",
        "x_3_1","x_3_2","x_3_4","x_3_5",
        "x_4_1","x_4_2","x_4_3","x_4_5",
        "x_5_1","x_5_2","x_5_3","x_5_4"
    ]

    solution = {key: float(variables[key].X) for key in order}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }