import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    regions = data["regions"]
    regions_int = [int(r) for r in regions]

    current = {int(k): v for k, v in data["current_cars"].items()}
    need = {int(k): v for k, v in data["cars_needed"].items()}

    move_cost_raw = data["move_cost"]
    move_cost = {}
    for key, val in move_cost_raw.items():
        i_str, j_str = key.split("_")
        i = int(i_str)
        j = int(j_str)
        move_cost[(i, j)] = val

    model = gp.Model("car_relocations")

    # Decision variables
    x = {}
    for i in regions_int:
        for j in regions_int:
            if i == j:
                continue
            x[(i, j)] = model.addVar(lb=0.0, name=f"x_{i}_{j}")

    model.update()

    # Objective: minimize total moving cost
    model.setObjective(
        gp.quicksum(move_cost[(i, j)] * x[(i, j)]
                    for i in regions_int for j in regions_int if i != j),
        GRB.MINIMIZE
    )

    # Constraints: final cars in each region >= cars_needed
    for r in regions_int:
        out_sum = gp.quicksum(x[(r, j)] for j in regions_int if j != r)
        in_sum = gp.quicksum(x[(i, r)] for i in regions_int if i != r)
        model.addConstr(current[r] - out_sum + in_sum >= need[r], name=f"need_{r}")

    # Prepare variables dict to return
    variables = {f"x_{i}_{j}": x[(i, j)] for i in regions_int for j in regions_int if i != j}

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status_code, str(status_code))
    objective = float(model.ObjVal)

    solution = {k: float(variables[k].X) for k in variables}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }