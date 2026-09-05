import gurobipy as gp

GRB = gp.GRB

def build_model(data: dict) -> tuple:
    regions = data["regions"]
    current = {int(k): v for k, v in data["current_cars"].items()}
    need = {int(k): v for k, v in data["cars_needed"].items()}
    move_cost = data["move_cost"]

    model = gp.Model("car_relocation")

    # Decision variables: x_i_j = cars moved from i to j (i != j)
    x = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            name = f"x_{i}_{j}"
            x[name] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=name)

    model.update()

    # Constraints: final cars in region r >= needs[r]
    for r in regions:
        sum_in = gp.quicksum(x[f"x_{i}_{r}"] for i in regions if i != r)
        sum_out = gp.quicksum(x[f"x_{r}_{j}"] for j in regions if j != r)
        model.addConstr(current[r] + sum_in - sum_out >= need[r], name=f"region_final_ge_{r}")

    # Objective: minimize total moving cost
    objective = gp.quicksum(move_cost[f"{i}_{j}"] * x[f"x_{i}_{j}"] for i in regions for j in regions if i != j)
    model.setObjective(objective, GRB.MINIMIZE)

    return model, x

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
    objective = int(round(model.ObjVal))

    solution = {
        "x_1_2": float(variables["x_1_2"].X),
        "x_1_3": float(variables["x_1_3"].X),
        "x_1_4": float(variables["x_1_4"].X),
        "x_1_5": float(variables["x_1_5"].X),
        "x_2_1": float(variables["x_2_1"].X),
        "x_2_3": float(variables["x_2_3"].X),
        "x_2_4": float(variables["x_2_4"].X),
        "x_2_5": float(variables["x_2_5"].X),
        "x_3_1": float(variables["x_3_1"].X),
        "x_3_2": float(variables["x_3_2"].X),
        "x_3_4": float(variables["x_3_4"].X),
        "x_3_5": float(variables["x_3_5"].X),
        "x_4_1": float(variables["x_4_1"].X),
        "x_4_2": float(variables["x_4_2"].X),
        "x_4_3": float(variables["x_4_3"].X),
        "x_4_5": float(variables["x_4_5"].X),
        "x_5_1": float(variables["x_5_1"].X),
        "x_5_2": float(variables["x_5_2"].X),
        "x_5_3": float(variables["x_5_3"].X),
        "x_5_4": float(variables["x_5_4"].X)
    }

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }