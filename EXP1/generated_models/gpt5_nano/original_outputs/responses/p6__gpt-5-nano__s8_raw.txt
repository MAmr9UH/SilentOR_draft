import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    regions = data["regions"]
    move_cost = data["move_cost"]
    current = data["current_cars"]
    needed = data["cars_needed"]

    # Create variables x_i_j for all i != j
    variables = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            var = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name=key)
            variables[key] = var

    # Objective: minimize total movement cost
    obj = gp.quicksum(move_cost[f"{i}_{j}"] * variables[f"x_{i}_{j}"]
                      for i in regions for j in regions if i != j)
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Constraints: final cars in each region >= cars_needed
    for k in regions:
        sum_in = gp.quicksum(variables[f"x_{i}_{k}"] for i in regions if i != k)
        sum_out = gp.quicksum(variables[f"x_{k}_{j}"] for j in regions if j != k)
        model.addConstr(current[str(k)] + sum_in - sum_out >= needed[str(k)])

    return model, variables

def solve(data: dict) -> dict:
    model, vars = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
        gp.GRB.INTERRUPTED: "INTERRUPTED"
    }
    status_str = status_map.get(status_code, str(status_code))

    solution = {
        "x_1_2": float(vars["x_1_2"].X),
        "x_1_3": float(vars["x_1_3"].X),
        "x_1_4": float(vars["x_1_4"].X),
        "x_1_5": float(vars["x_1_5"].X),
        "x_2_1": float(vars["x_2_1"].X),
        "x_2_3": float(vars["x_2_3"].X),
        "x_2_4": float(vars["x_2_4"].X),
        "x_2_5": float(vars["x_2_5"].X),
        "x_3_1": float(vars["x_3_1"].X),
        "x_3_2": float(vars["x_3_2"].X),
        "x_3_4": float(vars["x_3_4"].X),
        "x_3_5": float(vars["x_3_5"].X),
        "x_4_1": float(vars["x_4_1"].X),
        "x_4_2": float(vars["x_4_2"].X),
        "x_4_3": float(vars["x_4_3"].X),
        "x_4_5": float(vars["x_4_5"].X),
        "x_5_1": float(vars["x_5_1"].X),
        "x_5_2": float(vars["x_5_2"].X),
        "x_5_3": float(vars["x_5_3"].X),
        "x_5_4": float(vars["x_5_4"].X)
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result