import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    centers = data["centers"]  # c1..c7
    stores = data["stores"]    # s1..s4

    # Decision variables
    y = {}
    for idx, c in enumerate(centers, start=1):
        key = f"y_c{idx}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for idx, c in enumerate(centers, start=1):
        for s in stores:
            key = f"f_c{idx}_{s}"
            f[key] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)

    # Demand constraints: sum_c f_c_s == demand_s
    for s in stores:
        model.addConstr(quicksum(f[f"f_c{ci+1}_{s}"] for ci in range(len(centers))) == data["demand"][s])

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for ci, c in enumerate(centers, start=1):
        cap = data["capacity"][f"c{ci}"]
        model.addConstr(
            quicksum(f[f"f_c{ci}_{s}"] for s in stores) <= cap * y[f"y_c{ci}"]
        )

    # Objective: min opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    obj = quicksum(opening_costs[f"c{ci}"] * y[f"y_c{ci}"] for ci in range(1, len(centers) + 1))
    for ci, c in enumerate(centers, start=1):
        for s in stores:
            cost = data["transport_cost"][f"c{ci}"][s]
            obj += cost * f[f"f_c{ci}_{s}"]

    model.setObjective(obj, GRB.MINIMIZE)

    # Prepare return dictionary of variables
    variables = {}
    for ci in range(1, len(centers) + 1):
        variables[f"y_c{ci}"] = y[f"y_c{ci}"]
    for ci in range(1, len(centers) + 1):
        for s in stores:
            variables[f"f_c{ci}_{s}"] = f[f"f_c{ci}_{s}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    stat = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(stat, str(stat))

    model.update()

    # Build solution dictionary with all variable values
    solution = {}
    for i in range(1, 8):
        key = f"y_c{i}"
        solution[key] = variables[key].X
    for ci in range(1, 8):
        for s in data["stores"]:
            key = f"f_c{ci}_{s}"
            solution[key] = variables[key].X

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }