import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()
    try:
        model.setParam('OutputFlag', 0)
    except Exception:
        pass

    variables = {}

    # Opening decision variables
    for c in centers:
        key = f"y_{c}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Transportation variables
    for c in centers:
        for idx_s, s in enumerate(stores, start=1):
            key = f"f_{c}_s{idx_s}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s = demand_s for each store s
    for idx_s, s in enumerate(stores, start=1):
        demand_value = data["demand"][s]
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for c in centers)
        model.addConstr(expr == demand_value, name=f"Demand_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        capacity = data["capacity"][c]
        expr = gp.quicksum(variables[f"f_{c}_s{idx_s}"] for idx_s, _ in enumerate(stores, start=1))
        model.addConstr(expr <= capacity * variables[f"y_{c}"], name=f"Cap_{c}")

    # Objective: minimize total opening + transportation costs
    obj_open = gp.quicksum(data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in centers)
    obj_trans = gp.quicksum(
        data["transport_cost"][c][s] * variables[f"f_{c}_s{idx_s}"]
        for c in centers
        for idx_s, s in enumerate(stores, start=1)
    )
    model.setObjective(obj_open + obj_trans, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    solution = {}

    # y variables
    for c in data["centers"]:
        key = f"y_{c}"
        solution[key] = variables[key].X

    # f variables
    for c in data["centers"]:
        for idx_s, s in enumerate(data["stores"], start=1):
            key = f"f_{c}_s{idx_s}"
            solution[key] = variables[key].X

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }