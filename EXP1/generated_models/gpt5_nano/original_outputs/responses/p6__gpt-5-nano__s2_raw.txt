import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    regions = data.get("regions", [1, 2, 3, 4, 5])
    model = gp.Model()

    # Create decision variables: x_i_j for i != j
    variables = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            v = model.addVar(lb=0, vtype=GRB.INTEGER, name=key)
            variables[key] = v

    model.update()

    # Constraints: for each region r, current + incoming - outgoing >= needed
    for r in regions:
        in_sum = gp.quicksum(variables[f"x_{j}_{r}"] for j in regions if j != r)
        out_sum = gp.quicksum(variables[f"x_{r}_{j}"] for j in regions if j != r)
        current = data["current_cars"][str(r)]
        needed = data["cars_needed"][str(r)]
        model.addConstr(current + in_sum - out_sum >= needed, name=f"bal_{r}")

    # Objective: minimize total moving cost
    obj = gp.quicksum(data["move_cost"][f"{i}_{j}"] * variables[f"x_{i}_{j}"]
                      for i in regions for j in regions if i != j)
    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status_num, str(status_num))

    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    keys_order = [
        "x_1_2","x_1_3","x_1_4","x_1_5",
        "x_2_1","x_2_3","x_2_4","x_2_5",
        "x_3_1","x_3_2","x_3_4","x_3_5",
        "x_4_1","x_4_2","x_4_3","x_4_5",
        "x_5_1","x_5_2","x_5_3","x_5_4"
    ]
    solution = {}
    for k in keys_order:
        solution[k] = float(variables[k].X)

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }