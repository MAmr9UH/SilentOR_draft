from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = Model()

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, name=f"f_{c}_{s}", lb=0.0)

    model.update()

    # Demand constraints: meet exact demand at each store
    for s in stores:
        model.addConstr(quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: shipments from center c cannot exceed capacity if opened
    for c in centers:
        model.addConstr(quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost_expr = quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    transport_cost_expr = quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(opening_cost_expr + transport_cost_expr, GRB.MINIMIZE)

    # Flatten variables into a single dict with exact keys required
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

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

    # Build solution values for all required keys
    solution_keys = ["y_c1", "y_c2", "y_c3", "y_c4"]
    for c in data["centers"]:
        for s in data["stores"]:
            solution_keys.append(f"f_{c}_{s}")

    solution_values = {}
    for c in data["centers"]:
        solution_values[f"y_{c}"] = float(variables[f"y_{c}"].X)
    for c in data["centers"]:
        for s in data["stores"]:
            solution_values[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    # Build the required schema
    solution_schema = { key: {"type": "number"} for key in solution_keys }
    solution_schema_object = {
        "type": "object",
        "required": solution_keys,
        "properties": solution_schema
    }

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported objective value"},
            "solution": solution_schema_object
        }
    }

    result["status"] = status_str
    result["objective"] = float(model.ObjVal)

    # Attach actual values into the solution object
    result["solution"] = solution_values

    return result