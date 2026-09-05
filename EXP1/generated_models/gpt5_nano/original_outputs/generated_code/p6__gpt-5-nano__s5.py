import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    regions = data["regions"]
    model = gp.Model()

    # Create decision variables x_i_j for i != j
    x = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            x[key] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)

    model.update()

    # Objective: minimize total moving cost
    move_cost = data["move_cost"]
    obj_expr = gp.quicksum(move_cost[f"{i}_{j}"] * x[f"x_{i}_{j}"]
                           for i in regions for j in regions if i != j)
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # Balance constraints: final_i >= needed_i
    current = data["current_cars"]
    needed = data["cars_needed"]
    for i in regions:
        delta = needed[str(i)] - current[str(i)]
        inflow = gp.quicksum(x[f"x_{k}_{i}"] for k in regions if k != i)
        outflow = gp.quicksum(x[f"x_{i}_{k}"] for k in regions if k != i)
        model.addConstr(inflow - outflow >= delta, name=f"balance_{i}")

    return model, x

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status, str(status))

    # Objective value rounded
    obj_val = model.ObjVal if model.ObjVal is not None else 0.0
    objective_rounded = int(round(obj_val))

    # Read solution values and round to nearest integer
    order = [
        "x_1_2","x_1_3","x_1_4","x_1_5",
        "x_2_1","x_2_3","x_2_4","x_2_5",
        "x_3_1","x_3_2","x_3_4","x_3_5",
        "x_4_1","x_4_2","x_4_3","x_4_5",
        "x_5_1","x_5_2","x_5_3","x_5_4"
    ]
    solution_values = {}
    model.update()
    for key in order:
        solution_values[key] = int(round(variables[key].X))

    # Build solution schema with actual values
    solution_schema = {
        "type": "object",
        "required": order,
        "properties": { k: {"type": "number"} for k in order }
    }

    result = {
        "type": "object",
        "required": ["status","objective","solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number"},
            "solution": solution_schema
        },
        "status": status_str,
        "objective": objective_rounded,
        "solution": solution_values
    }

    return result