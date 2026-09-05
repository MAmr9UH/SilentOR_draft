import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Create decision variables
    variables = {}

    # Binary opening variables
    for c in centers:
        key = f"y_{c}"
        variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # Continuous shipment variables
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    objective = gp.quicksum(opening_cost[c] * variables[f"y_{c}"] for c in centers)
    for c in centers:
        for s in stores:
            objective += transport_cost[c][s] * variables[f"{c}_{s}"]

    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction at each store
    for s in stores:
        model.addConstr(gp.quicksum(variables[f"{c}_{s}"] for c in centers) == demand[s], name=f"Demand_{s}")

    # 2) Capacity constraints for each center (only ships if opened)
    for c in centers:
        model.addConstr(
            gp.quicksum(variables[f"{c}_{s}"] for s in stores) <= capacity[c] * variables[f"y_{c}"],
            name=f"Cap_{c}"
        )

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = float(model.ObjVal)

    centers = data["centers"]
    stores = data["stores"]
    # Build solution vector with exact keys
    solution_keys = [f"y_{c}" for c in centers] + [f"f_{c}_{s}" for c in centers for s in stores]

    model.update()
    solution = {}
    for k in solution_keys:
        solution[k] = float(variables[k].X)

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported objective value"},
            "solution": {
                "type": "object",
                "required": solution_keys,
                "properties": { key: {"type": "number"} for key in solution_keys }
            }
        }
    }

    # Return the structured result as per the required schema
    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }