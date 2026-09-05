import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum(data["fixed_opening_cost"][c] * y[c] for c in centers)
    transport_cost = gp.quicksum(data["transport_cost"][c][s] * f[(c, s)] for c in centers for s in stores)
    model.setObjective(opening_cost + transport_cost, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction at each store
    for s in stores:
        model.addConstr(gp.quicksum(f[(c, s)] for c in centers) == data["demand"][s], name=f"dem_{s}")

    # Capacity constraints for each center
    for c in centers:
        model.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= data["capacity"][c] * y[c], name=f"cap_{c}")

    # Prepare variables dictionary to return
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[(c, s)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status_str = status_map.get(model.Status, "UNKNOWN")

    # Build solution dict following required keys/order
    centers = data["centers"]
    stores = data["stores"]

    # Collect keys in exact required order
    solution_keys = []
    # y variables keys
    for c in centers:
        solution_keys.append(f"y_{c}")
    # f variables keys (c1_s1 ... c5_s9)
    for c in centers:
        for s in stores:
            solution_keys.append(f"f_{c}_{s}")

    solution = {}
    # Fill y values
    for c in centers:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    # Fill f values
    for c in centers:
        for s in stores:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    objective_value = float(model.ObjVal)

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported minimum total cost"},
            "solution": {
                "type": "object",
                "required": solution_keys,
                "properties": { key: {"type": "number"} for key in solution_keys }
            }
        }
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }