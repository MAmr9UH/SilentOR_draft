import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model("SupplyTek")

    centers = data["centers"]  # e.g., ["c1","c2",...]
    stores = data["stores"]    # e.g., ["s1","s2","s3","s4"]

    fixed_opening_cost = data["fixed_opening_cost"]  # dict: "c1" -> value
    transport_cost = data["transport_cost"]          # dict: "c1": {"s1": val, ...}, ...
    demand = data["demand"]                          # dict: "s1" -> value
    capacity = data["capacity"]                      # dict: "c1" -> value

    # Variables
    variables = {}

    # Opening decision variables y_c for each center
    y = {}
    for idx, c in enumerate(centers, start=1):
        var = model.addVar(vtype=GRB.BINARY, name=f"y_c{idx}")
        y[c] = var
        variables[f"y_c{idx}"] = var

    # Flow variables f_{c}_{s}
    f = {}
    for c in centers:
        for s in stores:
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")
            f[(c, s)] = var
            key = f"f_{c}_{s}"
            variables[key] = var

    model.update()

    # Objective: transportation costs + opening costs
    transport_term = quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    opening_term = quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    model.setObjective(transport_term + opening_term, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction at each store: sum_c f[c,s] == demand[s]
    for s in stores:
        model.addConstr(quicksum(f[(c, s)] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: sum_s f[c,s] <= capacity[c] * y[c]
    for c in centers:
        model.addConstr(quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    model.update()
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
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.CUTOFF: "CUTOFF"
    }
    st = model.Status
    status_str = status_map.get(st, str(st))

    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dict with exact keys
    solution_vals = {}

    # y variables
    for i in range(1, 8):
        key = f"y_c{i}"
        solution_vals[key] = float(variables[key].X)

    # f variables
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution_vals[key] = float(variables[key].X)

    # Prepare the JSON-schema-like structure to return
    solution_required = [f"y_c{i}" for i in range(1, 8)]
    solution_required += [f"f_{c}_{s}" for c in data["centers"] for s in data["stores"]]

    solution_properties = {key: {"type": "number"} for key in solution_required}

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported objective value"},
            "solution": {
                "type": "object",
                "required": solution_required,
                "properties": solution_properties
            }
        }
    }

    # Attach actual values in the solution object
    # The consumer expects the nested "solution" to contain the numeric values
    answer = {
        "status": status_str,
        "objective": obj_val,
        "solution": solution_vals
    }

    # Return in the requested schema shape
    result["solution"] = answer["solution"]
    # If the outer schema needs the inner object to be just the mapping, we set as above.
    # But to preserve the exact structure, return the full dictionary with nested values in "solution".
    final_output = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported objective value"},
            "solution": {
                "type": "object",
                "required": solution_required,
                "properties": solution_properties
            }
        }
    }

    # Merge actual values into the "solution" field of final_output
    final_output["status"] = status_str  # though not a field in the schema, place for compatibility
    final_output["objective"] = obj_val
    final_output["solution"] = solution_vals

    return final_output