import gurobipy as gp
from gurobipy import GRB
from typing import Tuple

def build_model(data: dict) -> Tuple[gp.Model, dict]:
    """
    Builds and returns the MILP model and a dictionary of all decision variables
    with EXACTLY the keys specified in the problem statement.
    """
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Decision variables
    variables = {}

    # Opening variables y_c1 ... y_c5
    for i in range(1, 6):
        key = f"y_c{i}"
        variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # Flow variables f_cx_sy
    for c_idx in range(1, 6):
        for s_idx in range(1, 10):
            key = f"f_c{c_idx}_s{s_idx}"
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Demand constraints: sum_c f_c_s = demand_s
    for s_idx in range(1, 10):
        demand_val = data["demand"][f"s{s_idx}"]
        lhs = gp.quicksum(variables[f"f_c{c}_s{s_idx}"] for c in range(1, 6))
        model.addConstr(lhs == demand_val, name=f"demand_s{s_idx}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c_idx in range(1, 6):
        cap = data["capacity"][f"c{c_idx}"]
        lhs = gp.quicksum(variables[f"f_c{c_idx}_s{s}"] for s in range(1, 10))
        model.addConstr(lhs <= cap * variables[f"y_c{c_idx}"], name=f"cap_c{c_idx}")

    # Objective: minimize fixed opening costs + transportation costs
    opening_cost_term = gp.quicksum(
        data["fixed_opening_cost"][f"c{c}"] * variables[f"y_c{c}"] for c in range(1, 6)
    )

    transport_cost_term = gp.quicksum(
        data["transport_cost"][f"c{c}"][f"s{s}"] * variables[f"f_c{c}_s{s}"]
        for c in range(1, 6) for s in range(1, 10)
    )

    model.setObjective(opening_cost_term + transport_cost_term, GRB.MINIMIZE)

    model.update()
    return model, variables

def _status_to_string(status_code: int) -> str:
    if status_code == GRB.OPTIMAL:
        return "OPTIMAL"
    if status_code == GRB.INFEASIBLE:
        return "INFEASIBLE"
    if status_code == GRB.UNBOUNDED:
        return "UNBOUNDED"
    if status_code == GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    if status_code == GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    return str(status_code)

def solve(data: dict) -> dict:
    """
    Builds the model, solves it, and returns results in the required schema.
    """
    model, variables = build_model(data)

    # Optimize
    model.optimize()

    status_str = _status_to_string(model.Status)
    obj_val = float(model.ObjVal)

    # Prepare solution dictionary with all required variable values
    solution = {}

    # y_c1 ... y_c5
    for c in range(1, 6):
        key = f"y_c{c}"
        solution[key] = float(variables[key].X)

    # f_c1_s1 ... f_c5_s9
    for c in range(1, 6):
        for s in range(1, 10):
            key = f"f_c{c}_s{s}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }