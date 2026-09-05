import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    centers = data["centers"]  # e.g., ["c1","c2",...]
    stores = data["stores"]    # e.g., ["s1","s2",...]
    n_centers = len(centers)
    n_stores = len(stores)

    # Decision variables
    y = {}
    for idx, c in enumerate(centers, start=1):
        key = f"y_{c}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for i, c in enumerate(centers, start=1):
        for j, s in enumerate(stores, start=1):
            key = f"f_c{i}_s{j}"
            f[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Demand constraints: sum over centers for each store equals demand
    for j, s in enumerate(stores, start=1):
        demand = data["demand"][s]
        model.addConstr(gp.quicksum(f[f"f_c{i}_s{j}"] for i in range(1, n_centers + 1)) == demand)

    # Capacity constraints: total flow from a center <= capacity * open_indicator
    for i, c in enumerate(centers, start=1):
        cap = data["capacity"][c]
        model.addConstr(gp.quicksum(f[f"f_c{i}_s{j}"] for j in range(1, n_stores + 1)) <= cap * y[f"y_{c}"])

    # Objective: open costs + transportation costs
    obj_open = gp.quicksum(data["fixed_opening_cost"][c] * y[f"y_{c}"] for c in centers)

    obj_transport = gp.quicksum(
        data["transport_cost"][c][stores[j-1]] * f[f"f_c{i}_s{j}"]
        for i, c in enumerate(centers, start=1)
        for j, s in enumerate(stores, start=1)
    )

    model.setObjective(obj_open + obj_transport, GRB.MINIMIZE)

    # Prepare output variables dict with exact keys
    variables = {}
    for k, v in y.items():
        variables[k] = v
    for k, v in f.items():
        variables[k] = v

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    model.update()
    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }