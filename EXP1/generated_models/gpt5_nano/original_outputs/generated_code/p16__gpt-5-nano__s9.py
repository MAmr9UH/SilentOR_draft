import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("SupplyTek")

    # Decision variables
    variables = {}

    # Opening variables y_c (binary)
    for idx, cid in enumerate(centers, start=1):
        key = f"y_{cid}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Transportation variables f_c_s (continuous, >= 0)
    for i, cid in enumerate(centers, start=1):
        for j, sid in enumerate(stores, start=1):
            key = f"f_{cid}_s{j}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)
            variables[key] = v

    model.update()

    # Objective: minimize opening costs + transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][cid] * variables[f"y_{cid}"] for cid in centers)
    for i, cid in enumerate(centers, start=1):
        for j, sid in enumerate(stores, start=1):
            cost = data["transport_cost"][cid][sid]
            obj += cost * variables[f"f_{cid}_s{j}"]

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # Demand constraints: sum over centers for each store >= demand
    for j, sid in enumerate(stores, start=1):
        model.addConstr(gp.quicksum(variables[f"f_{cid}_s{j}"] for cid in centers) >= data["demand"][sid],
                        name=f"demand_{sid}")

    # Capacity constraints: sum over stores <= capacity * y_c for each center
    for i, cid in enumerate(centers, start=1):
        cap = data["capacity"][cid]
        model.addConstr(gp.quicksum(variables[f"{cid}_s{j}"] if False else variables[f"f_{cid}_s{j}"] for j in range(1, len(stores) + 1)) <= cap * variables[f"y_{cid}"],
                        name=f"cap_{cid}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_str = "UNKNOWN"
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.NODE_LIMIT: "NODE_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.INTERMEDIATE: "INTERMEDIATE",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.CUTOFF: "CUTOFF",
        GRB.NONE: "NONE",
    }
    status_str = status_map.get(status_int, str(status_int))

    objective_value = model.ObjVal

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": float(objective_value),
        "solution": solution
    }