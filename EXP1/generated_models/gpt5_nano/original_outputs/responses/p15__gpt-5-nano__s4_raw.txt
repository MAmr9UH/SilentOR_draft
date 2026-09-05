import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    demand = data["demand"]
    capacity = data["capacity"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    model = gp.Model()

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Demand constraints: sum_c f_{c,s} = demand_s
    for s in stores:
        model.addConstr(quicksum(f[(c, s)] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        model.addConstr(quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    transport_costs = quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    model.setObjective(opening_cost + transport_costs, GRB.MINIMIZE)

    # Build variables dictionary with exact keys
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

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status_str = status_map.get(status_code, str(status_code))

    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with exact variable values
    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    # Build schema-enforced output
    solution_required_keys = [f"y_{c}" for c in data["centers"]] + \
                             [f"f_{c}_{s}" for c in data["centers"] for s in data["stores"]]

    top_schema = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported objective value"},
            "solution": {
                "type": "object",
                "required": solution_required_keys,
                "properties": {key: {"type": "number"} for key in solution_required_keys}
            }
        }
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }