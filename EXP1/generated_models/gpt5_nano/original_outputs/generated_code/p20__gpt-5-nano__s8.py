import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()
    centers = data["centers"]
    stores = data["stores"]

    # Flattened variables dictionary to return
    variables = {}

    # Decision variables: y_c (center open)
    y_vars = {}
    for ci in centers:
        key = f"y_{ci}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        y_vars[key] = v
        variables[key] = v

    # Transportation variables: f_c_s
    f_vars = {}
    for ci in centers:
        for si in stores:
            key = f"f_{ci}_{si}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            f_vars[key] = v
            variables[key] = v

    model.update()

    # Objective: minimize fixed opening costs + transportation costs
    opening_cost_term = gp.quicksum(data["fixed_opening_cost"][ci] * y_vars[f"y_{ci}"] for ci in centers)
    transport_cost_term = gp.quicksum(
        data["transport_cost"][ci][si] * f_vars[f"f_{ci}_{si}"] for ci in centers for si in stores
    )
    model.setObjective(opening_cost_term + transport_cost_term, GRB.MINIMIZE)

    # Constraints: Demand satisfaction
    for si in stores:
        model.addConstr(
            gp.quicksum(f_vars[f"f_{ci}_{si}"] for ci in centers) == data["demand"][si],
            name=f"dem_{si}"
        )

    # Constraints: Center capacity (only if opened)
    for ci in centers:
        model.addConstr(
            gp.quicksum(f_vars[f"f_{ci}_{si}"] for si in stores) <= data["capacity"][ci] * y_vars[f"y_{ci}"],
            name=f"cap_{ci}"
        )

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
    }
    status = status_map.get(model.Status, str(model.Status))

    model.update()
    objective = float(model.ObjVal)

    # Build solution dictionary matching required keys
    centers = data["centers"]
    stores = data["stores"]

    solution = {}

    for ci in centers:
        key = f"y_{ci}"
        solution[key] = float(variables[key].X)

    for ci in centers:
        for si in stores:
            key = f"f_{ci}_{si}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }