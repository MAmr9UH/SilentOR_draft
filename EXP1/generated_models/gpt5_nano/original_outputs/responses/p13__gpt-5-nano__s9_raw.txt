import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model("MarketFlow")

    # Decision variables
    y = {}  # open/close centers
    for cid in centers:
        key = f"y_{cid}"
        var = model.addVar(vtype=GRB.BINARY, name=key)
        y[cid] = var

    f = {}  # flow from center to store
    for cid in centers:
        for sid in stores:
            key = f"f_{cid}_{sid}"
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            f[(cid, sid)] = var

    # Objective: minimize opening costs plus transportation costs
    obj = gp.quicksum(opening_cost[cid] * y[cid] for cid in centers)
    obj += gp.quicksum(transport_cost[cid][sid] * f[(cid, sid)] for cid in centers for sid in stores)
    model.setObjective(obj, sense=GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction for each store
    for sid in stores:
        model.addConstr(gp.quicksum(f[(cid, sid)] for cid in centers) == demand[sid], name=f"Dem_{sid}")

    # 2) Center capacity must not be exceeded if the center is opened
    for cid in centers:
        model.addConstr(gp.quicksum(f[(cid, sid)] for sid in stores) <= capacity[cid] * y[cid], name=f"Cap_{cid}")

    # Return
    variables = {}
    for cid in centers:
        variables[f"y_{cid}"] = y[cid]
    for cid in centers:
        for sid in stores:
            variables[f"f_{cid}_{sid}"] = f[(cid, sid)]

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(st, str(st))

    solution = {k: float(v.X) for k, v in variables.items()}
    objective_value = float(model.ObjVal)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }