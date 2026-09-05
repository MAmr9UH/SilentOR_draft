import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    # Decision variables
    y = {}
    for i in range(1, len(centers) + 1):
        key = f"y_c{i}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            key = f"f_c{i}_s{j}"
            f[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)

    model.update()

    # Objective: opening costs + transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][f"c{idx}"] * y[f"y_c{idx}"] for idx in range(1, len(centers) + 1))
    for i in range(1, len(centers) + 1):
        center_key = f"c{i}"
        for j in range(1, len(stores) + 1):
            store_key = f"s{j}"
            cost = data["transport_cost"][center_key][store_key]
            obj += cost * f[f"f_c{i}_s{j}"]

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction
    for j in range(1, len(stores) + 1):
        demand = data["demand"][f"s{j}"]
        model.addConstr(gp.quicksum(f[f"f_c{i}_s{j}"] for i in range(1, len(centers) + 1)) == demand, name=f"dem_s{j}")

    # Capacity with opening decision
    for i in range(1, len(centers) + 1):
        cap = data["capacity"][f"c{i}"]
        model.addConstr(gp.quicksum(f[f"f_c{i}_s{j}"] for j in range(1, len(stores) + 1)) <= cap * y[f"y_c{i}"], name=f"cap_c{i}")

    # Prepare variables dictionary to return
    variables = {}
    for i in range(1, len(centers) + 1):
        variables[f"y_c{i}"] = y[f"y_c{i}"]
    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            variables[f"f_c{i}_s{j}"] = f[f"f_c{i}_s{j}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    obj_val = None
    try:
        obj_val = float(model.ObjVal)
    except:
        obj_val = None

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }