import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Create variables
    variables = {}

    # y variables (open centers)
    for i in range(1, 5):
        key = f"y_c{i}"
        variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # f variables (shipments from center to store)
    for i in range(1, 5):
        for j in range(1, 7):
            key = f"f_c{i}_s{j}"
            variables[key] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)

    model.update()

    # Demand constraints: sum over centers for each store equals demand
    stores = data["stores"]
    demand = data["demand"]
    for idx, s in enumerate(stores, start=1):
        demand_value = demand[s]
        expr = gp.quicksum(variables[f"f_c{c}_s{idx}"] for c in range(1, 5))
        model.addConstr(expr == demand_value, name=f"Demand_{s}")

    # Capacity constraints: sum over stores shipped from center <= capacity * y_center
    for c in range(1, 5):
        cap = data["capacity"][f"c{c}"]
        expr = gp.quicksum(variables[f"f_c{c}_s{j}"] for j in range(1, 7))
        model.addConstr(expr <= cap * variables[f"y_c{c}"], name=f"Capacity_c{c}")

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    obj = gp.quicksum(opening_costs[f"c{c}"] * variables[f"y_c{c}"] for c in range(1, 5))
    for c in range(1, 5):
        for sidx in range(1, 7):
            obj += transport_cost[f"c{c}"][f"s{sidx}"] * variables[f"f_c{c}_s{sidx}"]

    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    status_str = "UNKNOWN"
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNDEFINED or status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT_OR_UNDEFINED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.SUBOPTIMAL:
        status_str = "SUBOPTIMAL"
    else:
        status_str = str(status_code)

    model.update()

    # Build solution dictionary with required keys
    solution = {}

    # Order of keys must match exactly as specified in the prompt
    # y variables
    for i in range(1, 5):
        solution[f"y_c{i}"] = variables[f"y_c{i}"].X

    # f variables: f_c{ci}_s{si}
    for ci in range(1, 5):
        for si in range(1, 7):
            solution[f"f_c{ci}_s{si}"] = variables[f"f_c{ci}_s{si}"].X

    result = {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result