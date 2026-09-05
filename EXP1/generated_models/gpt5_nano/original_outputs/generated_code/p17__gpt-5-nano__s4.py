import gurobipy as gp
from typing import Dict, Tuple

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model("LogistiCorp")

    centers = data["centers"]
    stores = data["stores"]

    variables: Dict[str, object] = {}

    # Decision variables: y_c for each center
    for c in centers:
        key = f"y_{c}"
        v = model.addVar(vtype=gp.GRB.BINARY, name=key)
        variables[key] = v

    # Decision variables: f_c_s for each center-store pair
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            v = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Objective: minimize total opening plus transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in centers)

    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            cost = data["transport_cost"][c][s]
            obj += cost * variables[key]

    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction: sum_c f_{c,s} == demand_s
    for s in stores:
        model.addConstr(gp.quicksum(variables[f"f_{c}_{s}"] for c in centers) == data["demand"][s],
                        name=f"Demand_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        model.addConstr(gp.quicksum(variables[f"{'f_'+c+'_'+s}"] for s in stores) <=
                        data["capacity"][c] * variables[f"y_{c}"],
                        name=f"Cap_{c}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
    }
    status = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal)

    solution: dict = {}

    # y variables
    for c in data["centers"]:
        key = f"y_{c}"
        solution[key] = float(variables[key].X)

    # f variables
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }