import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    # Variables
    variables = {}

    # Opening variables y_c1 ... y_c6
    for idx, c in enumerate(centers, start=1):
        key = f"y_c{idx}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Transportation variables f_c{ci}_s{sj}
    for ci in range(1, len(centers) + 1):
        for sj in range(1, len(stores) + 1):
            key = f"f_c{ci}_s{sj}"
            v = model.addVar(vtype=GRB.CONTINUOUS, name=key, lb=0.0)
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s = demand_s
    for sj, s in enumerate(stores, start=1):
        constraint = gp.quicksum(variables[f"f_c{ci}_s{sj}"] for ci in range(1, len(centers) + 1))
        model.addConstr(constraint == data["demand"][s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for ci, c in enumerate(centers, start=1):
        capacity = data["capacity"][c]
        expr = gp.quicksum(variables[f"f_c{ci}_s{sj}"] for sj in range(1, len(stores) + 1))
        model.addConstr(expr <= capacity * variables[f"y_c{ci}"], name=f"cap_{ci}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    opening_sum = gp.quicksum(opening_cost[f"c{ci}"] * variables[f"y_c{ci}"] for ci in range(1, len(centers) + 1))
    transport_sum = gp.quicksum(
        transport_cost[f"c{ci}"][f"s{sj}"] * variables[f"f_c{ci}_s{sj}"]
        for ci in range(1, len(centers) + 1)
        for sj in range(1, len(stores) + 1)
    )

    model.setObjective(opening_sum + transport_sum, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNFEASIBLE: "UNFEASIBLE"  # alias, though GRB doesn't have UNFEASIBLE typically
    }
    status_str = status_map.get(status, str(status))

    # Read objective value
    objective = float(model.ObjVal) if model.SolCount > 0 else None
    if objective is None:
        objective = 0.0

    # Extract solution values
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }