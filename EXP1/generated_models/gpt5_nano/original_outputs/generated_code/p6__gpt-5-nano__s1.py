import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model("car_relocation")
    regions = data["regions"]
    move_cost = data["move_cost"]
    current = data["current_cars"]
    needs = data["cars_needed"]

    # Decision variables: x_i_j for i != j
    variables = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            variables[key] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=key)

    model.update()

    # Objective: minimize total moving cost
    obj = gp.quicksum(move_cost[f"{i}_{j}"] * variables[f"x_{i}_{j}"]
                      for i in regions for j in regions if i != j)
    model.setObjective(obj, GRB.MINIMIZE)

    # Balance constraints: inflow - outflow = needs - current
    for r in regions:
        inflow = gp.quicksum(variables[f"x_{i}_{r}"] for i in regions if i != r)
        outflow = gp.quicksum(variables[f"x_{r}_{j}"] for j in regions if j != r)
        delta = int(needs[str(r)]) - int(current[str(r)])
        model.addConstr(inflow - outflow == delta)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal)

    keys = [
        "x_1_2","x_1_3","x_1_4","x_1_5",
        "x_2_1","x_2_3","x_2_4","x_2_5",
        "x_3_1","x_3_2","x_3_4","x_3_5",
        "x_4_1","x_4_2","x_4_3","x_4_5",
        "x_5_1","x_5_2","x_5_3","x_5_4"
    ]
    solution = {k: float(variables[k].X) for k in keys}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }